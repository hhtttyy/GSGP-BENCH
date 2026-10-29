"""SBayesRC MCP server.

Exposes the SBayesRC R package (polygenic prediction with functional
annotations) as MCP tools. Scientific computation runs in the original R
package through ``Rscript``; this module implements the Python<->R contract.

Runtime configuration (environment variables, all optional):
  P2A_RSCRIPT    Rscript executable (default: "Rscript" or SBayesRC env path)
  P2A_R_PROJECT  absolute renv project with SBayesRC installed
                 (default: <repo>/r-runtime)
  P2A_PLINK2     plink2 binary used by the ``prs`` tool when no explicit path
                 is given (default: "plink2")

Run the server:  python sbayesrc.py
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP


REFERENCE = (
    "https://github.com/zhilizheng/SBayesRC/blob/"
    "2881f9a6f57374b80b4d19a09dbf9387939a2f46/vignettes/intro.Rmd"
)

_REPO = Path(__file__).resolve().parent.parent.parent


def _as_artifacts(outputs) -> list[dict]:
    """Normalize the dispatcher's ``outputs`` into existing absolute paths."""
    if isinstance(outputs, str):
        outputs = [outputs]
    if not isinstance(outputs, list):
        return []
    artifacts = []
    for item in outputs:
        if not isinstance(item, str) or not item:
            continue
        path = Path(item).expanduser()
        if not path.is_absolute():
            path = (_REPO / path)
        artifacts.append({"path": str(path), "exists": path.exists()})
    return artifacts


def _finalize(result: dict, message: str) -> dict:
    """Shape an R dispatcher result into the MCP structured return value."""
    result["artifacts"] = _as_artifacts(result.get("outputs"))
    result.pop("status", None)  # status is conveyed by success/absence of tool error
    result["message"] = message
    result["reference"] = REFERENCE
    return result

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
R_DISPATCHER = Path(__file__).resolve().parent.parent / "r_scripts" / "sbayesrc.R"
DEFAULT_R_PROJECT = REPO_ROOT / "r-runtime"
DEFAULT_RSCRIPT = os.environ.get("P2A_RSCRIPT", "Rscript")

mcp = FastMCP("SBayesRC")


def _require(path: str) -> dict:
    if not path or not Path(path).exists():
        raise ValueError(f"file not found: {path!r}")
    return path


def _call_r(tool: str, params: dict) -> dict:
    """Run the R dispatcher for ``tool`` with ``params`` and return its JSON."""
    rscript = os.environ.get("P2A_RSCRIPT", DEFAULT_RSCRIPT)
    params = dict(params)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(params, fh)
        params_path = fh.name
    try:
        env = dict(os.environ)
        default_project = env.get("P2A_R_PROJECT", str(DEFAULT_R_PROJECT))
        env["P2A_R_PROJECT"] = params.pop("_r_project", default_project)
        proc = subprocess.run(
            [rscript, str(R_DISPATCHER), tool, params_path],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=3600,
        )
        out = ""
        for line in proc.stdout.splitlines():
            out = line
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip().splitlines()
            detail = detail[-12:] if detail else []
            raise RuntimeError(
                f"R tool '{tool}' failed (rc={proc.returncode}): "
                f"{'; '.join(detail)}"
            )
        try:
            result = json.loads(out)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"R tool '{tool}' returned non-JSON on stdout: {proc.stdout[-500:]}"
            )
        if result.get("status") != "ok":
            raise RuntimeError(result.get("message", "unknown R error"))
        return result
    finally:
        Path(params_path).unlink(missing_ok=True)


@mcp.tool()
def tidy_summary(
    mafile: Annotated[str, "COJO-format GWAS summary file (SNP A1 A2 freq b se p N)"],
    ld_dir: Annotated[str, "SBayesRC LD reference folder containing snp.info"],
    output: Annotated[str, "Output path for the tidied summary"],
    freq_thresh: Annotated[float, "Max allele-frequency difference vs the LD reference"] = 0.2,
    N_sd_range: Annotated[float, "Keep SNPs within mean +/- this many SD of sample size"] = 3.0,
    rate2pq: Annotated[float, "Relative tolerance for the var-2pq ratio check"] = 0.5,
) -> dict:
    """Tidy/QC a COJO-format GWAS summary against an LD reference.
    Input is the raw summary + LD folder; output is a tidied summary file plus QC log.
    """
    _require(mafile)
    _require(ld_dir)
    return _finalize(_call_r("tidy", {
        "mafile": mafile, "ld_dir": ld_dir, "output": output,
        "freq_thresh": freq_thresh, "N_sd_range": N_sd_range,
        "rate2pq": rate2pq, "log2file": False,
    }), "Tidied COJO summary written; allele/QC flags in the log")


@mcp.tool()
def impute_summary(
    mafile: Annotated[str, "COJO-format GWAS summary file to impute"],
    ld_dir: Annotated[str, "SBayesRC LD reference folder containing snp.info"],
    output: Annotated[str, "Output path for the imputed summary (.ma)"],
    thresh: Annotated[float, "Eigen variance cutoff used for imputation"] = 0.995,
) -> dict:
    """Impute missing GWAS summary effects (b, se, p) from the LD reference.
    Input is a partial summary + LD folder; output is a summary covering every LD SNP.
    """
    _require(mafile)
    _require(ld_dir)
    return _finalize(_call_r("impute", {
        "mafile": mafile, "ld_dir": ld_dir, "output": output,
        "thresh": thresh, "log2file": False,
    }), "Imputed summary written (r2: 0=imputed, 1=typed)")


@mcp.tool()
def sbayesrc_run(
    mafile: Annotated[str, "COJO-format GWAS summary file (imputed/tidied)"],
    ld_dir: Annotated[str, "SBayesRC LD reference folder containing snp.info"],
    out_prefix: Annotated[str, "Output prefix for weights, parameters and annotation outputs"],
    annot: Annotated[str, "Functional annotation file (SNP + annotation columns); '' to run without"] = "",
    niter: Annotated[int, "Total number of MCMC iterations"] = 3000,
    burn: Annotated[int, "Number of MCMC burn-in iterations"] = 1000,
    tune_iter: Annotated[int, "Total number of tuning iterations"] = 150,
    tune_burn: Annotated[int, "Number of tuning burn-in iterations"] = 100,
    seed: Annotated[int, "Random seed passed to the R backend"] = 22,
    out_freq: Annotated[int, "Iteration frequency for writing parameter estimates"] = 10,
) -> dict:
    """Run the SBayesRC Bayesian mixture model for polygenic prediction.
    Input is a summary + LD reference (+ optional annotation); output is SNP weights,
    heritability/architecture parameters, and per-annotation enrichment artifacts.
    """
    _require(mafile)
    _require(ld_dir)
    if annot:
        _require(annot)
    return _finalize(_call_r("sbayesrc", {
        "mafile": mafile, "ld_dir": ld_dir, "out_prefix": out_prefix,
        "annot": annot, "niter": niter, "burn": burn,
        "tuneIter": tune_iter, "tuneBurn": tune_burn, "seed": seed,
        "outFreq": out_freq, "bOutDetail": False,
    }), "Weights in <outPrefix>.txt; heritability/architecture in .par")


@mcp.tool()
def prs(
    weight: Annotated[str, "SBayesRC SNP weight file (<outPrefix>.txt)"],
    geno_prefix: Annotated[str, "Genotype path prefix (.bed/.bim/.fam or .pgen/.pvar/.psam); {CHR} for per-chromosome"],
    out_prefix: Annotated[str, "Output prefix for <outPrefix>.score.txt"],
    geno_chr: Annotated[str, "Chromosome range for multi-file genotypes, e.g. 1-22,X"] = "",
    snplist: Annotated[str, "Optional file of variant IDs to extract"] = "",
    keepid: Annotated[str, "Optional file of FID IID samples to keep"] = "",
    plink2: Annotated[str, "plink2 binary path ('' -> $P2A_PLINK2 or 'plink2')"] = "",
) -> dict:
    """Compute polygenic risk scores with plink2 from SBayesRC weights.
    Input is a weight file + genotype; output is <outPrefix>.score.txt (FID IID ALLELE_CT SCORE).
    """
    _require(weight)
    return _finalize(_call_r("prs", {
        "weight": weight, "geno_prefix": geno_prefix, "out_prefix": out_prefix,
        "genoCHR": geno_chr, "snplist": snplist, "keepid": keepid,
        "tool": plink2, "log2file": False,
    }), "PRS in <outPrefix>.score.txt (FID IID ALLELE_CT SCORE)")


@mcp.tool()
def sbrc_multi(
    prs1: Annotated[str, "First PRS score file from sbayesrc_prs (ancestry 1)"],
    prs2: Annotated[str, "Second PRS score file from sbayesrc_prs (ancestry 2)"],
    out_prefix: Annotated[str, "Output prefix for the weighted score and weights"],
    tuneid: Annotated[str, "Tuning sample file (FID IID, no header)"],
    pheno: Annotated[str, "Phenotype file (FID IID pheno, no header)"],
    keepid: Annotated[str, "Optional file of FID IID samples to keep"] = "",
) -> dict:
    """Combine two ancestry-specific PRSs into a phenotype-weighted score (SBayesRC-multi).
    Input is two PRS files + tuning sample and phenotype; output is a weighted score and weights.
    """
    _require(prs1)
    _require(prs2)
    _require(tuneid)
    _require(pheno)
    return _finalize(_call_r("sbrcMulti", {
        "prs1": prs1, "prs2": prs2, "out_prefix": out_prefix,
        "tuneid": tuneid, "pheno": pheno, "keepid": keepid, "log2file": False,
    }), "Weighted PRS in <outPrefix>.score.txt; combination weights in .weight")


@mcp.tool()
def cut_ld(
    input_ld: Annotated[str, "Source SBayesRC LD reference folder"],
    output_ld: Annotated[str, "Destination folder for the reduced LD reference (must not exist)"],
    thresh: Annotated[float, "New eigen variance threshold (1.0 keeps the source threshold)"] = 1.0,
) -> dict:
    """Reduce an SBayesRC LD reference to a lower eigen variance threshold.
    Input is an LD reference folder; output is a smaller LD reference saved to output_ld.
    """
    _require(input_ld)
    return _finalize(_call_r("cutLD", {
        "input_ld": input_ld, "output_ld": output_ld,
        "thresh": thresh, "log2file": False,
    }), "Reduced LD reference written to output_ld")


if __name__ == "__main__":
    mcp.run()
