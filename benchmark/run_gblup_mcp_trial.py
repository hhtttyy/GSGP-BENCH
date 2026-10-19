#!/usr/bin/env python3
"""Run the GBLUP baseline through its local MCP and write an evidence record.

This closes the manual-baseline loop: MCP stdio → inspect → fit → export →
independent runner → gsgp.result.v1 → site JSON. The MCP never reads truth and
never computes metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate as validate_schema

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SERVER = REPO / "benchmark" / "algorithms" / "gblup" / "server.py"
DEFAULT_RUNNER = REPO / "agents" / "ifam" / "mcp" / "runner.py"
SCHEMA = REPO / "benchmark" / "schema" / "result.v1.json"


class Client:
    def __init__(self, base: Path, server: Path, run_root: Path) -> None:
        self.process = subprocess.Popen(
            [sys.executable, str(server), "--base-root", str(base), "--run-root", str(run_root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.next_id = 1
        self.initialize()

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        assert self.process.stdin and self.process.stdout
        request_id = self.next_id
        self.next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("GBLUP MCP exited: " + (self.process.stderr.read() if self.process.stderr else ""))
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(f"GBLUP MCP error: {response['error']}")
        return response["result"]

    def initialize(self) -> None:
        self.request(
            "initialize",
            {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "gblup-trial", "version": "0.1"}},
        )
        assert self.process.stdin
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(json.dumps(result.get("structuredContent"), ensure_ascii=False))
        return result["structuredContent"]

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.terminate()
        self.process.wait(timeout=5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="GBLUP baseline via MCP → evidence")
    parser.add_argument("--work-dir", default=str(REPO / "local_data" / "gblup-sim500"))
    parser.add_argument("--server", default=str(DEFAULT_SERVER))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--run-id", default="gblup-sim500-mcp-v1")
    parser.add_argument("--site-result", default=str(REPO / "site" / "data" / "results" / "gblup-sim500.json"))
    parser.add_argument("--evidence-dir", default=str(REPO / "benchmark" / "runs"))
    parser.add_argument("--dataset-manifest", default=str(REPO / "benchmark" / "datasets" / "sim500.json"))
    args = parser.parse_args()

    work = Path(args.work_dir).expanduser().resolve()
    base_args = {
        "input_root": ".",
        "bfile": "geno/demo",
        "phenotype": "pheno/phenotype.fit.txt",
        "phenotype_index": 2,
        "validation_split": "splits/repeat-1.json",
    }
    run_root = work / "mcp_runs"
    client = Client(work, Path(args.server), run_root)
    try:
        tools = client.request("tools/list")["tools"]
        inspect = client.call("gblup_inspect_inputs", base_args)
        fit = client.call("gblup_fit", base_args)
        export = client.call("gblup_export", {"run_id": fit["run_id"]})
    finally:
        client.close()

    predictions_path = work / "predictions_mcp.tsv"
    predictions_path.write_text(
        "sample_id\tgenetic_value\n"
        + "\n".join(f"{row['sample_id']}\t{row['genetic_value']:.10f}" for row in export["predictions"])
        + "\n",
        encoding="utf-8",
    )
    metrics_path = work / "metrics_mcp.json"
    runner = subprocess.run(
        [
            sys.executable,
            str(Path(args.runner)),
            "--predictions",
            str(predictions_path),
            "--truth",
            str(work / "pheno" / "phenotype.truth.txt"),
            "--fit-phenotype",
            str(work / "pheno" / "phenotype.fit.txt"),
            "--split",
            str(work / "splits" / "repeat-1.json"),
            "--out",
            str(metrics_path),
        ],
        capture_output=True,
        text=True,
    )
    if runner.returncode != 0:
        raise RuntimeError(f"runner failed: {runner.stdout}\n{runner.stderr}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    split = json.loads((work / "splits" / "repeat-1.json").read_text(encoding="utf-8"))
    evidence_run = Path(args.evidence_dir).expanduser().resolve() / args.run_id
    evidence_run.mkdir(parents=True, exist_ok=True)
    (evidence_run / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    result_path = evidence_run / "result.json"
    public_path = Path(args.site_result).expanduser().resolve()
    public_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": "gsgp.result.v1",
        "run_id": args.run_id,
        "algorithm": {
            "id": "gblup",
            "name": "GBLUP / rrBLUP",
            "implementation": "GSGP-Bench GBLUP v0.1 via MCP (manual baseline)",
            "paper_doi": "10.3168/jds.2007-0980",
            "paper_title": "VanRaden 2008, Efficient methods to compute genomic predictions, J. Dairy Sci. 91:4414–4423",
            "code_commit": None,
        },
        "dataset": {
            "id": "sim500",
            "name": "GSGP-Sim 500×5k",
            "species": "Sus scrofa (demo genotype)",
            "source": "Genotype: 500 individuals × 5,000 SNPs derived from the public upstream IFAM demo. Trait: simulated quantitative phenotype, h²=0.5, 200 causal SNPs, seed 20261019. Raw data stays local.",
            "n_individuals": inspect["counts"]["individuals"],
            "n_snps": inspect["counts"]["snps"],
            "trait": {"name": "simulated_trait", "type": "quantitative", "simulated": True, "heritability": 0.5},
            "license_note": "Raw genotype, phenotype and predictions remain local; only aggregate metrics and hashes are public.",
            "input_sha256": export["provenance"]["input_sha256"],
        },
        "split": {
            "split_id": split["split_id"],
            "seed": split.get("seed"),
            "n_training": fit["fit"]["n_training"],
            "n_validation": fit["fit"]["n_validation"],
            "split_sha256": export["provenance"]["input_sha256"]["splits/repeat-1.json"],
        },
        "metrics": {
            "pearson_r": metrics["metrics"]["pearson_r"],
            "r2": metrics["metrics"]["r2"],
            "prediction_bias_slope": metrics["metrics"]["prediction_bias_slope"],
            "auc": metrics["metrics"]["auc"],
            "runtime_seconds": fit["fit"]["runtime_seconds"],
        },
        "fit": fit["fit"],
        "evidence": {
            "level": "exploratory",
            "status": "complete",
            "certified": False,
            "single_split": True,
            "reviewed_by": None,
            "notes": [
                "Single 80/20 split; not a multi-fold L1 record.",
                "Produced through the manual GBLUP MCP over stdio; not a Paper2Agent-generated MCP.",
                "Trait is simulated; not the IFAM paper's Duroc phenotype.",
                "The MCP did not read truth and did not compute metrics; the independent runner did.",
            ],
        },
        "provenance": {
            "command": "python3 benchmark/run_gblup_mcp_trial.py --run-id " + args.run_id,
            "environment": export["provenance"]["environment"],
            "code_sha256": export["provenance"]["server_sha256"],
            "predictions_sha256": sha256(predictions_path),
            "runner_sha256": sha256(Path(args.runner).resolve()),
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "notes": ["MCP run artifact and public result are intentionally separate."],
        },
        "mcp": {
            "server": "gblup",
            "version": "0.1.0",
            "transport": "stdio",
            "tools": [tool["name"] for tool in tools],
            "fit_run_id": fit["run_id"],
        },
        "artifacts": {
            "result_json": f"benchmark/runs/{args.run_id}/result.json",
            "metrics_json": f"benchmark/runs/{args.run_id}/metrics.json",
            "site_json": "site/data/results/gblup-sim500.json",
            "predictions_private": "local_data/gblup-sim500/predictions_mcp.tsv",
        },
        "site": {"algorithm_id": "gblup", "dataset_id": "sim500", "status": "exploratory", "label": "单次划分 · 探索性"},
    }
    direct_path = REPO / "benchmark" / "runs" / "gblup-sim500-v1" / "result.json"
    if direct_path.is_file():
        direct = json.loads(direct_path.read_text(encoding="utf-8"))
        for key in ("pearson_r", "r2", "prediction_bias_slope"):
            if abs(result["metrics"][key] - direct["metrics"][key]) > 1e-6:
                raise RuntimeError(f"MCP result differs from direct baseline on {key}")
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    public_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    dataset_manifest = {
        "schema_version": "gsgp.dataset.v1",
        "id": "sim500",
        "name": "GSGP-Sim 500×5k",
        "species": "Sus scrofa (demo genotype)",
        "source": result["dataset"]["source"],
        "n_individuals": result["dataset"]["n_individuals"],
        "n_snps": result["dataset"]["n_snps"],
        "trait": result["dataset"]["trait"],
        "split": result["split"],
        "input_sha256": result["dataset"]["input_sha256"],
        "license_note": result["dataset"]["license_note"],
        "local_path": "local_data/gblup-sim500",
    }
    Path(args.dataset_manifest).write_text(json.dumps(dataset_manifest, indent=2) + "\n", encoding="utf-8")
    validate_schema(result, json.loads(SCHEMA.read_text(encoding="utf-8")))
    print(json.dumps({"run_id": result["run_id"], "metrics": result["metrics"], "mcp": result["mcp"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
