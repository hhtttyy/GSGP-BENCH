#!/usr/bin/env python3
"""Fast MCP plumbing validation without R or HIBLUP.

This is intentionally NOT an IFAM execution. It uses stub_runtime/Rscript.stub
to exercise the real MCP stdio server, job lifecycle, export, truth boundary and
independent runner. Every exported record is marked runtime_mode="stub".

Use acceptance.py for the real engineering acceptance after R/HIBLUP exist.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from acceptance import MCPClient  # noqa: E402


def _filter_validation_truth(source: Path, split_path: Path, target: Path) -> None:
    split = json.loads(split_path.read_text(encoding="utf-8"))
    validation = set(split["validation_ids"])
    lines = source.read_text(encoding="utf-8").splitlines()
    selected = [lines[0]] + [line for line in lines[1:] if line.split("\t")[0] in validation]
    target.write_text("\n".join(selected) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IFAM MCP stub dry-run (not IFAM evidence)")
    parser.add_argument("--tiny-root", default=str(HERE / "fixtures" / "tiny"))
    parser.add_argument("--upstream-root", default=os.environ.get("IFAM_ROOT"))
    parser.add_argument("--work-dir", default="/tmp/ifam-mcp-dry-run")
    parser.add_argument(
        "--driver",
        choices=["auto", "ifam-r", "stub-r"],
        default="auto",
        help="ifam-r uses the real IFAM.R + fake HIBLUP; stub-r uses a fake Rscript",
    )
    args = parser.parse_args(argv)

    tiny = Path(args.tiny_root).expanduser().resolve()
    upstream = Path(args.upstream_root).expanduser().resolve() if args.upstream_root else None
    if upstream is None or not (upstream / "Scripts" / "IFAM.R").is_file():
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": "IFAM_ROOT must point at the extracted IFAM-main checkout (the real IFAM.R hash is checked before the worker runs)",
                },
                indent=2,
            )
        )
        return 2
    driver = args.driver
    rscript = shutil.which("Rscript")
    if driver == "auto":
        driver = "ifam-r" if rscript else "stub-r"
    if driver == "ifam-r" and not rscript:
        print(json.dumps({"status": "blocked", "error": "ifam-r driver needs Rscript on PATH"}, indent=2))
        return 2
    work = Path(args.work_dir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    jobs = work / "jobs"
    stub = HERE / "stub_runtime"
    if driver == "ifam-r":
        driver_env = {
            "RSCRIPT": str(rscript),
            "HIBLUP": str(stub / "hiblup"),
            "HIBLUP_VERSION": "fake-engine",
        }
        driver_note = "real IFAM.R 1.0.0 orchestration + fake HIBLUP numerical engine"
    else:
        driver_env = {
            "RSCRIPT": str(stub / "Rscript.stub"),
            "HIBLUP": str(stub / "hiblup.stub"),
            "HIBLUP_VERSION": "stub-runtime",
        }
        driver_note = "fake IFAM.R + fake HIBLUP"
    client = None
    steps: list[dict[str, Any]] = []

    def step(name: str, status: str, detail: str = "", **extra: Any) -> None:
        steps.append({"name": name, "status": status, "detail": detail, **extra})

    try:
        client = MCPClient(
            tiny,
            upstream,
            jobs,
            extra_env={
                "IFAM_MCP_STUB": "1",
                **driver_env,
            },
        )
        init = client.initialize()
        step("mcp_initialize", "pass", f"{init['serverInfo']['name']} {init['serverInfo']['version']}")
        listed = client.request("tools/list")
        names = [tool["name"] for tool in listed["tools"]]
        step("tools_list", "pass", ", ".join(names))
        expected = json.loads((tiny / "expected" / "inspect_inputs.json").read_text(encoding="utf-8"))
        inspected = client.call(
            "ifam_inspect_inputs",
            {
                "input_root": ".",
                "bfile": "geno/tiny",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "special_annotations": ["trait_snps"],
                "random_max": 5,
                "validation_split": "splits/repeat-1.json",
            },
        )
        if inspected != expected:
            raise RuntimeError("inspect output differs from the golden JSON")
        step("inspect_tiny_golden", "pass", "exact match")
        fit = client.call(
            "ifam_fit",
            {
                "input_root": ".",
                "bfile": "geno/tiny",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "special_annotations": ["trait_snps"],
                "random_max": 5,
                "validation_split": "splits/repeat-1.json",
                "vc_method": "AI",
                "threads": 1,
                "keep_intermediate": False,
            },
        )
        job_id = fit["job_id"]
        step("fit_submit", "pass", job_id)
        status = None
        deadline = time.time() + 30
        while time.time() < deadline:
            status = client.call("ifam_job_status", {"job_id": job_id})
            if status["state"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.1)
        if not status or status["state"] != "succeeded":
            raise RuntimeError(f"stub fit did not succeed: {status}")
        step("job_status", "pass", f"{status['state']} / {status['phase']}")
        if driver == "ifam-r":
            log_path = jobs / job_id / "run.log"
            log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
            if "IFAM is end" not in log_text or "Version: 1.0.0" not in log_text:
                raise RuntimeError("real IFAM.R log did not reach the expected end marker")
            step("ifam_r_orchestration", "pass", "real IFAM.R 1.0.0 reached 'IFAM is end'")
        export = client.call("ifam_export", {"job_id": job_id})
        if export["provenance"].get("runtime_mode") != "stub":
            raise RuntimeError("export is missing the stub provenance marker")
        if "metrics" in export or "pearson_r" in export:
            raise RuntimeError("MCP export must not contain metrics")
        if len(export["validation_ids"]) != 4:
            raise RuntimeError("unexpected validation ID count")
        (work / "export.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
        step(
            "export",
            "pass",
            f"{export['n_predictions']} predictions; runtime_mode=stub; no metrics",
        )
    except Exception as exc:  # noqa: BLE001
        step("mcp_flow", "fail", f"{type(exc).__name__}: {exc}")
        report = {
            "schema_version": "ifam.dry-run.v1",
            "status": "failed",
            "execution_mode": "stub",
            "driver": driver,
            "driver_note": driver_note,
            "scientific_evidence": False,
            "steps": steps,
        }
        (work / "dry_run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        if client:
            client.close()
        return 1
    finally:
        if client:
            client.close()

    validation_truth = work / "validation_truth.txt"
    _filter_validation_truth(
        tiny / "pheno" / "phenotype.truth.txt",
        tiny / "splits" / "repeat-1.json",
        validation_truth,
    )
    runner_out = work / "evaluation.json"
    runner = subprocess.run(
        [
            sys.executable,
            str(HERE / "runner.py"),
            "--predictions",
            str(work / "export.json"),
            "--truth",
            str(validation_truth),
            "--fit-phenotype",
            str(tiny / "pheno" / "phenotype.fit.txt"),
            "--split",
            str(tiny / "splits" / "repeat-1.json"),
            "--out",
            str(runner_out),
        ],
        capture_output=True,
        text=True,
    )
    if runner.returncode != 0 or not runner_out.is_file():
        step("independent_runner", "fail", runner.stdout + runner.stderr)
        report = {
            "schema_version": "ifam.dry-run.v1",
            "status": "failed",
            "execution_mode": "stub",
            "driver": driver,
            "driver_note": driver_note,
            "scientific_evidence": False,
            "steps": steps,
        }
        (work / "dry_run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1
    evaluation = json.loads(runner_out.read_text(encoding="utf-8"))
    step(
        "independent_runner",
        "pass",
        f"n={evaluation['n_validation']} metrics={evaluation['metrics']}",
    )
    step("policy", "pass", "truth stayed outside MCP; export contains no metrics")
    report = {
        "schema_version": "ifam.dry-run.v1",
        "status": "passed",
        "execution_mode": "stub",
        "driver": driver,
        "driver_note": driver_note,
        "scientific_evidence": False,
        "mcp_transport": "stdio",
        "note": "This validates MCP plumbing and, with ifam-r, the real IFAM.R orchestration. It uses a fake numerical engine, is not IFAM/HIBLUP execution, not a reproduction, and must not be published as evidence.",
        "steps": steps,
        "evaluation": evaluation,
    }
    (work / "dry_run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (work / "dry_run_report.md").write_text(
        "# IFAM MCP stub dry-run\n\n"
        "Status: **passed**\n\n"
        f"Driver: `{driver}` — {driver_note}.\n\n"
        "This run used a fake numerical engine. It is not IFAM/HIBLUP execution and is not scientific evidence.\n\n"
        + "\n".join(f"- **{item['name']}**: {item['status']} — {item.get('detail', '')}" for item in steps)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
