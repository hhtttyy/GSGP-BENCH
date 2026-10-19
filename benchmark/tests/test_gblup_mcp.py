from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "benchmark" / "algorithms" / "gblup" / "server.py"
DATA = REPO / "local_data" / "gblup-sim500"


@unittest.skipUnless(DATA.is_dir(), "local GBLUP sim500 data is absent")
class GblupMCPIntegrationTests(unittest.TestCase):
    def test_inspect_fit_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.Popen(
                [sys.executable, str(SERVER), "--base-root", str(DATA), "--run-root", temporary],
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
                args = {
                    "input_root": ".",
                    "bfile": "geno/demo",
                    "phenotype": "pheno/phenotype.fit.txt",
                    "phenotype_index": 2,
                    "validation_split": "splits/repeat-1.json",
                }
                calls = [
                    ("gblup_inspect_inputs", args),
                    ("gblup_fit", args),
                ]
                request_id = 2
                results = {}
                for name, arguments in calls:
                    process.stdin.write(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "method": "tools/call",
                                "params": {"name": name, "arguments": arguments},
                            }
                        )
                        + "\n"
                    )
                    process.stdin.flush()
                    result = json.loads(process.stdout.readline())["result"]
                    self.assertFalse(result["isError"])
                    results[name] = result["structuredContent"]
                    request_id += 1
                fit = results["gblup_fit"]
                self.assertEqual(len(fit["predictions"]), 100)
                self.assertNotIn("metrics", fit)
                self.assertFalse(any("truth" in key.lower() for key in fit["provenance"]["input_sha256"]))
                process.stdin.write(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "method": "tools/call",
                            "params": {"name": "gblup_export", "arguments": {"run_id": fit["run_id"]}},
                        }
                    )
                    + "\n"
                )
                process.stdin.flush()
                export = json.loads(process.stdout.readline())["result"]
                self.assertFalse(export["isError"])
                self.assertEqual(export["structuredContent"]["run_id"], fit["run_id"])
            finally:
                process.terminate()
                process.wait(timeout=5)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream:
                        stream.close()


if __name__ == "__main__":
    unittest.main()
