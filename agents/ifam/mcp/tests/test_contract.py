from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_ROOT))

import ifam_core  # noqa: E402
import runner  # noqa: E402


class InspectContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = json.loads(
            (MCP_ROOT / "fixtures" / "tiny" / "expected" / "inspect_inputs.json").read_text(encoding="utf-8")
        )

    def test_inspect_matches_golden(self) -> None:
        actual, _ = ifam_core.inspect_dataset(
            MCP_ROOT,
            input_root="fixtures/tiny",
            bfile="geno/tiny",
            phenotype="pheno/phenotype.fit.txt",
            phenotype_index=2,
            annotation_dir="annotations",
            special_annotations=["trait_snps"],
            random_max=5,
            validation_split="splits/repeat-1.json",
        )
        self.assertEqual(actual, self.expected)

    def test_fixture_manifest_hashes(self) -> None:
        fixture_root = MCP_ROOT / "fixtures" / "tiny"
        manifest = json.loads((fixture_root / "fixture.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["files_sha256"].items():
            digest = hashlib.sha256((fixture_root / relative).read_bytes()).hexdigest()
            self.assertEqual(digest, expected, relative)

    def test_no_annotation_names_manifest(self) -> None:
        self.assertFalse((MCP_ROOT / "fixtures" / "tiny" / "annotations" / "annotation_names.txt").exists())

    def test_truth_is_not_an_mcp_input(self) -> None:
        tools = json.loads((MCP_ROOT / "tools.json").read_text(encoding="utf-8"))
        for tool in tools["tools"]:
            properties = tool["inputSchema"].get("properties", {})
            self.assertFalse(any("truth" in name for name in properties), tool["name"])

    def test_two_special_annotations_rejected(self) -> None:
        with self.assertRaises(ifam_core.IfamError) as raised:
            ifam_core.inspect_dataset(
                MCP_ROOT,
                input_root="fixtures/tiny",
                bfile="geno/tiny",
                phenotype="pheno/phenotype.fit.txt",
                annotation_dir="annotations",
                special_annotations=["trait_snps", "enhancer"],
                random_max=5,
            )
        self.assertEqual(raised.exception.code, "SPECIAL_ANNOTATION_INVALID")


class RunnerTests(unittest.TestCase):
    def _write(self, root: Path, predictions: list[dict], truth: str, split: dict) -> tuple[Path, Path, Path]:
        pred_path = root / "predictions.json"
        truth_path = root / "truth.txt"
        split_path = root / "split.json"
        pred_path.write_text(json.dumps({"predictions": predictions}), encoding="utf-8")
        truth_path.write_text(truth, encoding="utf-8")
        split_path.write_text(json.dumps(split), encoding="utf-8")
        return pred_path, truth_path, split_path

    def test_pearson_and_slope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            predictions = [
                {"sample_id": "A", "genetic_value": 1.0},
                {"sample_id": "B", "genetic_value": 2.0},
                {"sample_id": "C", "genetic_value": 3.0},
                {"sample_id": "D", "genetic_value": 4.0},
            ]
            split = {"split_id": "t", "training_ids": ["X"], "validation_ids": ["A", "B", "C", "D"]}
            paths = self._write(root, predictions, "ID\ttrait\nA\t2\nB\t4\nC\t6\nD\t8\n", split)
            report = runner.evaluate(*paths)
            self.assertEqual(report["metrics"]["pearson_r"], 1.0)
            self.assertEqual(report["metrics"]["prediction_bias_slope"], 2.0)
            self.assertIsNone(report["metrics"]["auc"])

    def test_auc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            predictions = [
                {"sample_id": "A", "genetic_value": 0.1},
                {"sample_id": "B", "genetic_value": 0.4},
                {"sample_id": "C", "genetic_value": 0.35},
                {"sample_id": "D", "genetic_value": 0.8},
            ]
            split = {"split_id": "t", "training_ids": ["X"], "validation_ids": ["A", "B", "C", "D"]}
            paths = self._write(root, predictions, "ID\ttrait\nA\t0\nB\t0\nC\t1\nD\t1\n", split)
            report = runner.evaluate(*paths)
            self.assertAlmostEqual(report["metrics"]["auc"], 0.75)

    def test_truth_outside_validation_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            predictions = [{"sample_id": "A", "genetic_value": 1.0}]
            split = {"split_id": "t", "training_ids": ["B"], "validation_ids": ["A"]}
            paths = self._write(root, predictions, "ID\ttrait\nA\t1\nB\t2\n", split)
            with self.assertRaises(runner.EvaluationError) as raised:
                runner.evaluate(*paths)
            self.assertEqual(raised.exception.code, "TRUTH_OUTSIDE_VALIDATION")

    def test_fit_phenotype_leakage_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            predictions = [{"sample_id": "A", "genetic_value": 1.0}]
            split = {"split_id": "t", "training_ids": ["B"], "validation_ids": ["A"]}
            paths = self._write(root, predictions, "ID\ttrait\nA\t1\n", split)
            fit = root / "fit.txt"
            fit.write_text("ID\ttrait\nA\t1\nB\t2\n", encoding="utf-8")
            with self.assertRaises(runner.EvaluationError) as raised:
                runner.evaluate(*paths, fit_phenotype_path=fit)
            self.assertEqual(raised.exception.code, "VALIDATION_LEAKAGE")


class StdioTests(unittest.TestCase):
    def test_stdio_inspect(self) -> None:
        process = subprocess.Popen(
            [sys.executable, str(MCP_ROOT / "server.py"), "--base-root", str(MCP_ROOT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            assert process.stdin and process.stdout
            process.stdin.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}},
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())["id"], 1)
            process.stdin.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "ifam_inspect_inputs",
                            "arguments": {
                                "input_root": "fixtures/tiny",
                                "bfile": "geno/tiny",
                                "phenotype": "pheno/phenotype.fit.txt",
                                "annotation_dir": "annotations",
                                "special_annotations": ["trait_snps"],
                                "random_max": 5,
                                "validation_split": "splits/repeat-1.json",
                            },
                        },
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            result = json.loads(process.stdout.readline())["result"]
            self.assertFalse(result["isError"])
            self.assertEqual(result["structuredContent"]["status"], "ready")
        finally:
            process.terminate()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()


if __name__ == "__main__":
    unittest.main()
