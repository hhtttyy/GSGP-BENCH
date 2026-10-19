#!/usr/bin/env python3
"""Fill the IFAM × sim500 cell with a clearly labeled STUB record.

This runs the real IFAM.R 1.0.0 orchestration through the local IFAM MCP, but
uses the fake HIBLUP engine from agents/ifam/mcp/stub_runtime. The numbers are
not scientific evidence. They exist to demonstrate the Paper2Agent/MCP chain
while HIBLUP v1.1.0 is unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate as validate_schema

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agents" / "ifam" / "mcp"))
from acceptance import MCPClient  # noqa: E402

SCHEMA = REPO / "benchmark" / "schema" / "result.v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_inputs(source: Path, annotations_source: Path, target: Path) -> None:
    for directory in ("geno", "pheno", "annotations", "splits"):
        (target / directory).mkdir(parents=True, exist_ok=True)
    for extension in ("bed", "bim", "fam"):
        source_path = source / "geno" / f"demo.{extension}"
        target_path = target / "geno" / f"demo.{extension}"
        if not target_path.exists():
            try:
                os.link(source_path, target_path)
            except OSError:
                shutil.copy2(source_path, target_path)
    for name in ("phenotype.fit.txt", "phenotype.truth.txt"):
        shutil.copy2(source / "pheno" / name, target / "pheno" / name)
    shutil.copy2(source / "splits" / "repeat-1.json", target / "splits" / "repeat-1.json")
    for path in sorted(annotations_source.glob("*.txt")):
        shutil.copy2(path, target / "annotations" / path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="IFAM × sim500 stub record")
    parser.add_argument("--source", default=str(REPO / "local_data" / "gblup-sim500"))
    parser.add_argument("--annotations-source", default=str(REPO / "local_data" / "ifam-demo-500x5k" / "annotations"))
    parser.add_argument("--work-dir", default=str(REPO / "local_data" / "ifam-stub-sim500"))
    parser.add_argument("--ifam-root", default=str(Path.home() / "Downloads" / "IFAM-main"))
    parser.add_argument("--run-id", default="ifam-stub-sim500-v1")
    parser.add_argument("--site-result", default=str(REPO / "site" / "data" / "results" / "ifam-stub-sim500.json"))
    parser.add_argument("--evidence-dir", default=str(REPO / "benchmark" / "runs"))
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    annotations = Path(args.annotations_source).expanduser().resolve()
    work = Path(args.work_dir).expanduser().resolve()
    upstream = Path(args.ifam_root).expanduser().resolve()
    if not (upstream / "Scripts" / "IFAM.R").is_file():
        raise SystemExit(f"missing IFAM.R under {upstream}; pass --ifam-root")
    prepare_inputs(source, annotations, work)
    rscript = shutil.which("Rscript")
    if not rscript:
        raise SystemExit("Rscript is required for the IFAM stub run")
    stub = REPO / "agents" / "ifam" / "mcp" / "stub_runtime"
    job_root = work / "jobs"
    client = MCPClient(
        work,
        upstream,
        job_root,
        extra_env={
            "IFAM_MCP_STUB": "1",
            "RSCRIPT": rscript,
            "HIBLUP": str(stub / "hiblup"),
            "HIBLUP_VERSION": "fake-engine",
        },
    )
    try:
        client.initialize()
        tools = [tool["name"] for tool in client.request("tools/list")["tools"]]
        inspect = client.call(
            "ifam_inspect_inputs",
            {
                "input_root": ".",
                "bfile": "geno/demo",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "random_max": 5,
                "validation_split": "splits/repeat-1.json",
            },
        )
        fit = client.call(
            "ifam_fit",
            {
                "input_root": ".",
                "bfile": "geno/demo",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "random_max": 5,
                "vc_method": "AI",
                "threads": 2,
                "validation_split": "splits/repeat-1.json",
            },
        )
        deadline = time.time() + 600
        status = None
        while time.time() < deadline:
            status = client.call("ifam_job_status", {"job_id": fit["job_id"]})
            if status["state"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(1)
        if not status or status["state"] != "succeeded":
            raise RuntimeError(json.dumps(status, ensure_ascii=False)[:2000])
        export = client.call("ifam_export", {"job_id": fit["job_id"]})
    finally:
        client.close()

    predictions_path = work / "predictions_stub.tsv"
    predictions_path.write_text(
        "sample_id\tgenetic_value\n"
        + "\n".join(f"{row['sample_id']}\t{row['genetic_value']:.10f}" for row in export["predictions"])
        + "\n",
        encoding="utf-8",
    )
    metrics_path = work / "metrics_stub.json"
    runner = subprocess.run(
        [
            sys.executable,
            str(REPO / "agents" / "ifam" / "mcp" / "runner.py"),
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
        raise RuntimeError(runner.stdout + runner.stderr)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    split = json.loads((work / "splits" / "repeat-1.json").read_text(encoding="utf-8"))
    evidence_dir = Path(args.evidence_dir).expanduser().resolve() / args.run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    result_path = evidence_dir / "result.json"
    site_path = Path(args.site_result).expanduser().resolve()
    site_path.parent.mkdir(parents=True, exist_ok=True)
    r_version = subprocess.run([rscript, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    result = {
        "schema_version": "gsgp.result.v1",
        "run_id": args.run_id,
        "algorithm": {
            "id": "ifam",
            "name": "IFAM",
            "implementation": "IFAM.R 1.0.0 + fake HIBLUP (STUB runtime)",
            "paper_doi": "10.1038/s41467-026-72470-0",
            "paper_title": "Tang et al. 2026, Improving genomic prediction accuracy of complex traits by integrating massive types of functional annotation information, Nature Communications 17:5686",
            "code_commit": "62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649",
        },
        "dataset": {
            "id": "sim500",
            "name": "GSGP-Sim 500×5k",
            "species": "Sus scrofa (demo genotype)",
            "source": "Genotype and annotations derived from the public upstream IFAM demo (500 individuals × 5,000 SNPs); trait simulated with h²=0.5, 200 causal SNPs, seed 20261019. Raw data stays local.",
            "n_individuals": inspect["counts"]["individuals"],
            "n_snps": inspect["counts"]["snps"],
            "trait": {"name": "simulated_trait", "type": "quantitative", "simulated": True, "heritability": 0.5},
            "license_note": "STUB record. Fake HIBLUP engine; raw data and predictions remain local; no scientific claim.",
            "input_sha256": export["provenance"]["input_sha256"],
        },
        "split": {
            "split_id": split["split_id"],
            "seed": split.get("seed"),
            "n_training": len(split["training_ids"]),
            "n_validation": len(split["validation_ids"]),
            "split_sha256": export["provenance"]["split_sha256"],
        },
        "metrics": {
            "pearson_r": metrics["metrics"]["pearson_r"],
            "r2": metrics["metrics"]["r2"],
            "prediction_bias_slope": metrics["metrics"]["prediction_bias_slope"],
            "auc": metrics["metrics"]["auc"],
            "runtime_seconds": None,
        },
        "fit": {
            "runtime_mode": "stub",
            "variance_components": export.get("variance_components", []),
            "random_effects": export.get("random_effects"),
            "annotation_summary": export.get("annotation_summary"),
        },
        "evidence": {
            "level": "stub",
            "status": "complete",
            "certified": False,
            "single_split": True,
            "reviewed_by": None,
            "notes": [
                "STUB ONLY: real IFAM.R orchestration, fake HIBLUP numerical engine.",
                "Numbers are not IFAM results and must not be cited as scientific evidence.",
                "This fills the Paper2Agent/MCP lane for capability display while HIBLUP v1.1.0 is unavailable.",
                "Independent runner computed metrics from held-out truth.",
            ],
        },
        "provenance": {
            "command": "python3 benchmark/run_ifam_stub_sim.py --run-id " + args.run_id,
            "environment": {
                "python": platform.python_version(),
                "R": r_version,
                "hiblup": "fake-engine",
                "platform": platform.platform(),
            },
            "code_sha256": export["provenance"]["ifam_r_sha256"],
            "predictions_sha256": sha256(predictions_path),
            "runner_sha256": sha256(REPO / "agents" / "ifam" / "mcp" / "runner.py"),
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "notes": ["runtime_mode=stub", "IFAM job " + fit["job_id"]],
        },
        "mcp": {
            "server": "ifam",
            "version": "0.1.0",
            "transport": "stdio",
            "tools": tools,
            "job_id": fit["job_id"],
        },
        "artifacts": {
            "result_json": f"benchmark/runs/{args.run_id}/result.json",
            "metrics_json": f"benchmark/runs/{args.run_id}/metrics.json",
            "site_json": "site/data/results/ifam-stub-sim500.json",
            "predictions_private": "local_data/ifam-stub-sim500/predictions_stub.tsv",
        },
        "site": {"algorithm_id": "ifam", "dataset_id": "sim500", "status": "stub", "label": "STUB · fake HIBLUP"},
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    site_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    validate_schema(result, json.loads(SCHEMA.read_text(encoding="utf-8")))
    print(json.dumps({"run_id": result["run_id"], "metrics": result["metrics"], "evidence": result["evidence"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
