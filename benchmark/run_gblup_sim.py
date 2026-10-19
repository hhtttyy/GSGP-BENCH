#!/usr/bin/env python3
"""Run a real GBLUP baseline on a simulated trait.

The genotype data is a local subset of the public upstream IFAM demo (500
individuals, 5,000 SNPs). The trait is simulated with a known heritability so
this run is an engineering/benchmark baseline, not a reproduction of the IFAM
paper's Duroc trait.

The raw genotype, phenotype and predictions stay under local_data/ (gitignored).
Only aggregate metrics, hashes and provenance are written to the public result
record under site/data/results/ and benchmark/runs/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER = REPO / "agents" / "ifam" / "mcp" / "runner.py"
DEFAULT_SCHEMA = REPO / "benchmark" / "schema" / "result.v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_fam(path: Path) -> list[str]:
    return [line.split()[0] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_snps(path: Path) -> list[str]:
    return [line.split()[1] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_genotypes(prefix: Path) -> tuple[list[str], list[str], np.ndarray, int]:
    fam = read_fam(prefix.with_suffix(".fam"))
    snps = read_snps(prefix.with_suffix(".bim"))
    n, m = len(fam), len(snps)
    data = prefix.with_suffix(".bed").read_bytes()
    width = (n + 3) // 4
    if data[:3] != b"\x6c\x1b\x01" or len(data) != 3 + m * width:
        raise RuntimeError("invalid PLINK bed")
    arr = np.frombuffer(data, dtype=np.uint8, offset=3).reshape(m, width)
    codes = (arr[:, :, None] >> np.array([0, 2, 4, 6], dtype=np.uint8)) & 3
    codes = codes.reshape(m, width * 4)[:, :n]
    dosage = np.full(codes.shape, np.nan, dtype=np.float64)
    dosage[codes == 0] = 0.0
    dosage[codes == 2] = 1.0
    dosage[codes == 3] = 2.0
    missing = int(np.isnan(dosage).sum())
    means = np.nanmean(dosage, axis=1, keepdims=True)
    dosage = np.where(np.isnan(dosage), means, dosage)
    return fam, snps, dosage.T, missing  # individuals x SNPs


def simulate_trait(
    dosage: np.ndarray,
    fam: list[str],
    seed: int,
    h2: float,
    n_causal: int,
) -> tuple[np.ndarray, list[int], list[int]]:
    rng = np.random.default_rng(seed)
    maf = dosage.mean(axis=0) / 2
    eligible = np.flatnonzero((maf > 0.05) & (maf < 0.95))
    if len(eligible) < n_causal:
        raise RuntimeError("not enough polymorphic SNPs for the simulation")
    causal = rng.choice(eligible, size=n_causal, replace=False)
    effects = rng.normal(0, 1, size=n_causal)
    genetic = dosage[:, causal] @ effects
    genetic = (genetic - genetic.mean()) / genetic.std()
    phenotype = math.sqrt(h2) * genetic + math.sqrt(1 - h2) * rng.normal(0, 1, size=dosage.shape[0])
    phenotype = (phenotype - phenotype.mean()) / phenotype.std()
    permutation = rng.permutation(dosage.shape[0])
    n_val = max(1, round(dosage.shape[0] * 0.2))
    validation_idx = [int(i) for i in permutation[:n_val]]
    training_idx = [int(i) for i in permutation[n_val:]]
    return phenotype, training_idx, validation_idx


def gblup_reml(
    dosage: np.ndarray,
    phenotype: np.ndarray,
    training_idx: list[int],
    validation_idx: list[int],
) -> tuple[np.ndarray, dict[str, Any]]:
    maf = dosage.mean(axis=0) / 2
    keep = (maf > 0) & (maf < 1)
    x = dosage[:, keep]
    p = x.mean(axis=0) / 2
    z = x - 2 * p
    denominator = 2 * float(np.sum(p * (1 - p)))
    if denominator <= 0:
        raise RuntimeError("GRM denominator is zero")
    grm = (z @ z.T) / denominator
    train = np.asarray(training_idx, dtype=int)
    val = np.asarray(validation_idx, dtype=int)
    y = phenotype[train]
    gtt = grm[np.ix_(train, train)]
    gvt = grm[np.ix_(val, train)]
    eigenvalues, eigenvectors = np.linalg.eigh(gtt)
    eigenvalues = np.clip(eigenvalues, 1e-8, None)
    ones = np.ones(len(train))

    def negative_reml(log_lambda: float) -> float:
        lam = math.exp(log_lambda)
        inv = 1.0 / (eigenvalues + lam)
        vinv1 = eigenvectors @ (inv * (eigenvectors.T @ ones))
        denom = float(ones @ vinv1)
        beta = float(ones @ (eigenvectors @ (inv * (eigenvectors.T @ y)))) / denom
        residual = y - beta
        vinv_r = eigenvectors @ (inv * (eigenvectors.T @ residual))
        py = vinv_r - vinv1 * (float(ones @ vinv_r) / denom)
        ypy = float(y @ py)
        n = len(y)
        return 0.5 * (
            (n - 1) * math.log(max(ypy / (n - 1), 1e-30))
            + float(np.log(eigenvalues + lam).sum())
            + math.log(max(denom, 1e-30))
        )

    optimum = minimize_scalar(negative_reml, bounds=(-12, 12), method="bounded", options={"xatol": 1e-8})
    lam = math.exp(float(optimum.x))
    inv = 1.0 / (eigenvalues + lam)
    vinv1 = eigenvectors @ (inv * (eigenvectors.T @ ones))
    denom = float(ones @ vinv1)
    beta = float(ones @ (eigenvectors @ (inv * (eigenvectors.T @ y)))) / denom
    residual = y - beta
    vinv_r = eigenvectors @ (inv * (eigenvectors.T @ residual))
    predictions = gvt @ vinv_r
    ypy = float(residual @ (vinv_r - vinv1 * (float(ones @ vinv_r) / denom)))
    sigma_e2 = ypy / (len(y) - 1)
    sigma_g2 = sigma_e2 / lam
    return predictions, {
        "lambda": lam,
        "sigma_g2": sigma_g2,
        "sigma_e2": sigma_e2,
        "n_snps": int(dosage.shape[1]),
        "n_snps_used": int(keep.sum()),
        "n_training": int(len(train)),
        "n_validation": int(len(val)),
        "reml_objective": float(optimum.fun),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a real GBLUP baseline on a simulated trait")
    parser.add_argument("--source-subset", default=str(REPO / "local_data" / "ifam-demo-500x5k"))
    parser.add_argument("--work-dir", default=str(REPO / "local_data" / "gblup-sim500"))
    parser.add_argument("--run-id", default="gblup-sim500-v1")
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--h2", type=float, default=0.5)
    parser.add_argument("--causal-snps", type=int, default=200)
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--site-result", default=str(REPO / "site" / "data" / "results" / "gblup-sim500.json"))
    parser.add_argument("--evidence-dir", default=str(REPO / "benchmark" / "runs"))
    args = parser.parse_args(argv)

    source = Path(args.source_subset).expanduser().resolve()
    work = Path(args.work_dir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    geno_dir = work / "geno"
    pheno_dir = work / "pheno"
    split_dir = work / "splits"
    for directory in (geno_dir, pheno_dir, split_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for extension in ("bed", "bim", "fam"):
        source_path = source / "geno" / f"demo.{extension}"
        target_path = geno_dir / f"demo.{extension}"
        if not target_path.exists():
            shutil.copy2(source_path, target_path)
    prefix = geno_dir / "demo"
    fam, snps, dosage, missing = read_genotypes(prefix)
    phenotype, training_idx, validation_idx = simulate_trait(
        dosage, fam, args.seed, args.h2, args.causal_snps
    )
    train_ids = [fam[i] for i in training_idx]
    val_ids = [fam[i] for i in validation_idx]
    header = "ID\ttrait"
    (pheno_dir / "phenotype.fit.txt").write_text(
        header + "\n" + "\n".join(f"{fam[i]}\t{'NA' if i in set(validation_idx) else f'{phenotype[i]:.8f}'}" for i in range(len(fam))) + "\n",
        encoding="utf-8",
    )
    (pheno_dir / "phenotype.truth.txt").write_text(
        header + "\n" + "\n".join(f"{fam[i]}\t{phenotype[i]:.8f}" for i in validation_idx) + "\n",
        encoding="utf-8",
    )
    split = {
        "schema_version": "gsgp.split.v1",
        "split_id": "sim500-repeat-1",
        "seed": args.seed,
        "training_ids": train_ids,
        "validation_ids": val_ids,
    }
    (split_dir / "repeat-1.json").write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")

    started = time.time()
    predictions, fit = gblup_reml(dosage, phenotype, training_idx, validation_idx)
    runtime = time.time() - started
    predictions_path = work / "predictions.tsv"
    predictions_path.write_text(
        "sample_id\tgenetic_value\n" + "\n".join(f"{fam[i]}\t{value:.8f}" for i, value in zip(validation_idx, predictions)) + "\n",
        encoding="utf-8",
    )
    metrics_path = work / "metrics.json"
    runner_cmd = [
        sys.executable,
        str(Path(args.runner)),
        "--predictions",
        str(predictions_path),
        "--truth",
        str(pheno_dir / "phenotype.truth.txt"),
        "--fit-phenotype",
        str(pheno_dir / "phenotype.fit.txt"),
        "--split",
        str(split_dir / "repeat-1.json"),
        "--out",
        str(metrics_path),
    ]
    runner_proc = subprocess.run(runner_cmd, capture_output=True, text=True)
    if runner_proc.returncode != 0:
        raise RuntimeError(f"runner failed: {runner_proc.stdout}\n{runner_proc.stderr}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    input_files = {
        "geno/demo.bed": geno_dir / "demo.bed",
        "geno/demo.bim": geno_dir / "demo.bim",
        "geno/demo.fam": geno_dir / "demo.fam",
        "pheno/phenotype.fit.txt": pheno_dir / "phenotype.fit.txt",
        "pheno/phenotype.truth.txt": pheno_dir / "phenotype.truth.txt",
        "splits/repeat-1.json": split_dir / "repeat-1.json",
    }
    input_hashes = {name: sha256(path) for name, path in input_files.items()}
    run_id = args.run_id
    evidence_run_dir = Path(args.evidence_dir).expanduser().resolve() / run_id
    evidence_run_dir.mkdir(parents=True, exist_ok=True)
    public_result_path = Path(args.site_result).expanduser().resolve()
    public_result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path = evidence_run_dir / "result.json"
    metrics_public_path = evidence_run_dir / "metrics.json"
    metrics_public_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    code_hash = sha256(Path(__file__).resolve())
    runner_hash = sha256(Path(args.runner).resolve())
    result = {
        "schema_version": "gsgp.result.v1",
        "run_id": run_id,
        "algorithm": {
            "id": "gblup",
            "name": "GBLUP / rrBLUP",
            "implementation": "GSGP-Bench GBLUP v0.1 (VanRaden GRM, single random effect REML)",
            "paper_doi": "10.3168/jds.2007-0980",
            "paper_title": "VanRaden 2008, Efficient methods to compute genomic predictions, J. Dairy Sci. 91:4414–4423",
            "code_commit": None,
        },
        "dataset": {
            "id": "sim500",
            "name": "GSGP-Sim 500×5k",
            "species": "Sus scrofa (demo genotype)",
            "source": "Genotype: 500 individuals × 5,000 SNPs derived from the public upstream IFAM demo. Trait: simulated quantitative phenotype, h²=0.5, 200 causal SNPs, seed 20261019. Raw data stays local.",
            "n_individuals": int(dosage.shape[0]),
            "n_snps": int(dosage.shape[1]),
            "trait": {
                "name": "simulated_trait",
                "type": "quantitative",
                "simulated": True,
                "heritability": args.h2,
            },
            "license_note": "Raw genotype, phenotype and predictions remain local; only aggregate metrics and hashes are public.",
            "input_sha256": input_hashes,
        },
        "split": {
            "split_id": split["split_id"],
            "seed": args.seed,
            "n_training": len(train_ids),
            "n_validation": len(val_ids),
            "split_sha256": input_hashes["splits/repeat-1.json"],
        },
        "metrics": {
            "pearson_r": metrics["metrics"]["pearson_r"],
            "r2": metrics["metrics"]["r2"],
            "prediction_bias_slope": metrics["metrics"]["prediction_bias_slope"],
            "auc": metrics["metrics"]["auc"],
            "runtime_seconds": round(runtime, 4),
        },
        "fit": {
            **fit,
            "missing_genotypes_imputed": missing,
            "simulation_causal_snps": args.causal_snps,
            "simulation_seed": args.seed,
        },
        "evidence": {
            "level": "exploratory",
            "status": "complete",
            "certified": False,
            "single_split": True,
            "reviewed_by": None,
            "notes": [
                "Single 80/20 split; not a multi-fold L1 record.",
                "Trait is simulated; not the IFAM paper's Duroc phenotype.",
                "Genotype subset derives from the public upstream demo and is not committed.",
                "No held-out truth was read by the MCP or by the fitting code; the independent runner computed the metrics.",
            ],
        },
        "provenance": {
            "command": "python3 benchmark/run_gblup_sim.py --run-id " + run_id,
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": __import__("scipy").__version__,
                "platform": platform.platform(),
            },
            "code_sha256": code_hash,
            "predictions_sha256": sha256(predictions_path),
            "runner_sha256": runner_hash,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "notes": [
                "Prediction and truth files are local only.",
                "Runner output was computed outside the fitting code.",
            ],
        },
        "artifacts": {
            "result_json": f"benchmark/runs/{run_id}/result.json",
            "metrics_json": f"benchmark/runs/{run_id}/metrics.json",
            "predictions_private": "local_data/gblup-sim500/predictions.tsv",
        },
        "site": {
            "algorithm_id": "gblup",
            "dataset_id": "sim500",
            "status": "exploratory",
            "label": "单次划分 · 探索性",
        },
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    public_result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    try:
        import jsonschema

        schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(result, schema)
    except ImportError:
        pass
    print(json.dumps({k: result[k] for k in ("run_id", "metrics", "evidence")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
