#!/usr/bin/env python3
"""Minimal GBLUP MCP server over stdio.

This is a manual baseline service, not a Paper2Agent-generated MCP. It wraps
the same GBLUP/REML code used by the evidence trial. The fit tool never reads
held-out truth and never computes benchmark metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from benchmark.run_gblup_sim import gblup_reml, read_genotypes  # noqa: E402

SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
RUN_ID = re.compile(r"^gblup-\d{8}-[0-9a-f]{8}$")
TOOLS = json.loads((HERE / "tools.json").read_text(encoding="utf-8"))


class GblupError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(base: Path, relative: str, label: str, allow_dot: bool = False) -> Path:
    if not relative:
        raise GblupError("PATH_NOT_ALLOWED", f"{label} is empty")
    if relative == "." and allow_dot:
        return base
    if os.path.isabs(relative) or ".." in Path(relative).parts or not SAFE_PATH.fullmatch(relative):
        raise GblupError("PATH_NOT_ALLOWED", f"{label} is not a safe relative path: {relative!r}")
    path = (base / relative).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise GblupError("PATH_NOT_ALLOWED", f"{label} escapes the input root") from exc
    return path


def run_root() -> Path:
    raw = os.environ.get("GBLUP_MCP_RUN_ROOT", "/tmp/gblup-mcp-runs")
    if not SAFE_PATH.fullmatch(raw):
        raise GblupError("PATH_NOT_ALLOWED", "GBLUP_MCP_RUN_ROOT contains unsafe characters")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_phenotype(path: Path, column: int) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise GblupError("PHENOTYPE_INVALID", "phenotype is empty")
    header = lines[0].split("\t")
    if column < 2 or column > len(header):
        raise GblupError("PHENOTYPE_INVALID", "phenotype_index is outside the header")
    values: dict[str, float | None] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < len(header):
            raise GblupError("PHENOTYPE_INVALID", "short phenotype row")
        sample_id = fields[0].strip()
        raw = fields[column - 1].strip()
        if sample_id in values:
            raise GblupError("ID_MISMATCH", f"duplicate phenotype ID {sample_id}")
        if raw.upper() == "NA":
            values[sample_id] = None
        else:
            try:
                value = float(raw)
            except ValueError as exc:
                raise GblupError("PHENOTYPE_INVALID", f"{sample_id} is not numeric or NA") from exc
            if not math.isfinite(value):
                raise GblupError("PHENOTYPE_INVALID", f"{sample_id} is not finite")
            values[sample_id] = value
    return {"header": header, "column": column, "values": values}


def read_split(path: Path | None, pheno: dict[str, float | None]) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GblupError("VALIDATION_SPLIT_INVALID", "split must be an object")
    split_id = payload.get("split_id")
    training = payload.get("training_ids")
    validation = payload.get("validation_ids")
    if not isinstance(split_id, str) or not isinstance(training, list) or not isinstance(validation, list):
        raise GblupError("VALIDATION_SPLIT_INVALID", "split needs split_id, training_ids, validation_ids")
    training = [str(value) for value in training]
    validation = [str(value) for value in validation]
    if len(set(training)) != len(training) or len(set(validation)) != len(validation):
        raise GblupError("VALIDATION_SPLIT_INVALID", "split IDs must be unique")
    if set(training) & set(validation):
        raise GblupError("VALIDATION_SPLIT_INVALID", "training and validation overlap")
    missing = (set(training) | set(validation)) - set(pheno)
    if missing:
        raise GblupError("VALIDATION_SPLIT_INVALID", f"split IDs absent from phenotype: {sorted(missing)[:5]}")
    leaked = [sample_id for sample_id in validation if pheno[sample_id] is not None]
    if leaked:
        raise GblupError("VALIDATION_LEAKAGE", f"{len(leaked)} validation IDs still have a numeric fit phenotype")
    return {"split_id": split_id, "training_ids": training, "validation_ids": validation}


def load_inputs(base: Path, args: dict[str, Any]) -> dict[str, Any]:
    input_root = resolve(base, args.get("input_root", "."), "input_root", allow_dot=True)
    if not input_root.is_dir():
        raise GblupError("INPUT_NOT_FOUND", "input_root is not a directory")
    bfile_rel = args.get("bfile")
    phenotype_rel = args.get("phenotype")
    if not bfile_rel or not phenotype_rel:
        raise GblupError("INPUT_NOT_FOUND", "bfile and phenotype are required")
    bfile = resolve(input_root, bfile_rel, "bfile")
    phenotype_path = resolve(input_root, phenotype_rel, "phenotype")
    for extension in (".bed", ".bim", ".fam"):
        if not bfile.with_suffix(extension).is_file():
            raise GblupError("INPUT_NOT_FOUND", f"missing {bfile.name}{extension}")
    if not phenotype_path.is_file():
        raise GblupError("INPUT_NOT_FOUND", "phenotype is missing")
    pheno = read_phenotype(phenotype_path, int(args.get("phenotype_index", 2)))
    split_path = None
    if args.get("validation_split"):
        split_path = resolve(input_root, args["validation_split"], "validation_split")
        if not split_path.is_file():
            raise GblupError("INPUT_NOT_FOUND", "validation split is missing")
    split = read_split(split_path, pheno["values"])
    fam, snps, dosage, missing = read_genotypes(bfile)
    if set(pheno["values"]) != set(fam):
        raise GblupError("ID_MISMATCH", "phenotype and .fam IDs differ")
    return {
        "input_root": input_root,
        "bfile_rel": bfile_rel,
        "bfile": bfile,
        "phenotype_rel": phenotype_rel,
        "phenotype_path": phenotype_path,
        "pheno": pheno,
        "split_path": split_path,
        "split": split,
        "fam": fam,
        "snps": snps,
        "dosage": dosage,
        "missing": missing,
    }


def inspect_tool(base: Path, args: dict[str, Any]) -> dict[str, Any]:
    data = load_inputs(base, args)
    n, m = data["dosage"].shape
    warnings = []
    if data["missing"]:
        warnings.append({"code": "MISSING_GENOTYPES_IMPUTED", "message": f"{data['missing']} missing genotypes will be mean-imputed"})
    checks = [
        {"id": "plink_present", "status": "pass"},
        {"id": "phenotype_header", "status": "pass"},
        {"id": "phenotype_ids_match_fam", "status": "pass"},
        {"id": "split_ids_disjoint", "status": "pass" if data["split"] else "not_applicable"},
        {"id": "validation_phenotypes_masked", "status": "pass" if data["split"] else "not_applicable"},
    ]
    return {
        "schema_version": "gblup.inspect.v1",
        "status": "ready",
        "counts": {"individuals": n, "snps": m},
        "phenotype": {
            "file": data["phenotype_rel"],
            "column_index": data["pheno"]["column"],
            "column_name": data["pheno"]["header"][data["pheno"]["column"] - 1],
            "numeric_values": sum(1 for value in data["pheno"]["values"].values() if value is not None),
            "missing_values": sum(1 for value in data["pheno"]["values"].values() if value is None),
        },
        "split": data["split"],
        "checks": checks,
        "warnings": warnings,
    }


def fit_tool(base: Path, args: dict[str, Any]) -> dict[str, Any]:
    data = load_inputs(base, args)
    split = data["split"]
    if split is None:
        raise GblupError("VALIDATION_SPLIT_REQUIRED", "gblup_fit requires validation_split for a validation prediction")
    fam = data["fam"]
    index = {sample_id: i for i, sample_id in enumerate(fam)}
    pheno = data["pheno"]["values"]
    training = split["training_ids"]
    validation = split["validation_ids"]
    if any(pheno[sample_id] is None for sample_id in training):
        raise GblupError("TRAINING_PHENOTYPE_MISSING", "training IDs must have numeric phenotypes")
    y = np.array(
        [float(pheno[sample_id]) if pheno[sample_id] is not None else np.nan for sample_id in fam]
    )
    train_idx = [index[sample_id] for sample_id in training]
    val_idx = [index[sample_id] for sample_id in validation]
    started = time.time()
    predictions, fit = gblup_reml(data["dosage"], y, train_idx, val_idx)
    runtime = time.time() - started
    run_id = f"gblup-{datetime.now().strftime('%Y%m%d')}-{os.urandom(4).hex()}"
    run_dir = run_root() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    input_files = {
        "geno/demo.bed": data["bfile"].with_suffix(".bed"),
        "geno/demo.bim": data["bfile"].with_suffix(".bim"),
        "geno/demo.fam": data["bfile"].with_suffix(".fam"),
        "pheno/phenotype.fit.txt": data["phenotype_path"],
        "splits/repeat-1.json": data["split_path"],
    }
    input_hashes = {name: sha256(path) for name, path in input_files.items() if path is not None}
    output = {
        "schema_version": "gblup.fit.v1",
        "run_id": run_id,
        "predictions": [
            {"sample_id": sample_id, "genetic_value": float(value)}
            for sample_id, value in zip(validation, predictions)
        ],
        "validation_ids": validation,
        "n_predictions": len(validation),
        "fit": {**fit, "runtime_seconds": round(runtime, 6), "missing_genotypes_imputed": data["missing"]},
        "provenance": {
            "paper_doi": "10.3168/jds.2007-0980",
            "paper_title": "VanRaden 2008, Efficient methods to compute genomic predictions, J. Dairy Sci. 91:4414–4423",
            "implementation": "GSGP-Bench GBLUP v0.1 via MCP",
            "server_sha256": sha256(Path(__file__)),
            "runner_sha256": None,
            "input_sha256": input_hashes,
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "platform": platform.platform(),
            },
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "notes": ["Manual baseline MCP; no truth read; no metrics computed."],
        },
    }
    (run_dir / "run.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def export_tool(base: Path, args: dict[str, Any]) -> dict[str, Any]:
    run_id = str(args.get("run_id", ""))
    if not RUN_ID.fullmatch(run_id):
        raise GblupError("JOB_NOT_FOUND", "invalid GBLUP run ID")
    path = run_root() / run_id / "run.json"
    if not path.is_file():
        raise GblupError("JOB_NOT_FOUND", f"unknown GBLUP run {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
    try:
        import jsonschema

        jsonschema.validate(arguments, tool["inputSchema"])
    except ImportError:
        for key in tool["inputSchema"].get("required", []):
            if key not in arguments:
                raise GblupError("VALIDATION_ERROR", f"missing required argument {key}")
    except Exception as exc:
        raise GblupError("VALIDATION_ERROR", str(exc)) from exc


def call_tool(name: str, arguments: dict[str, Any], base: Path) -> Any:
    tools = {tool["name"]: tool for tool in TOOLS["tools"]}
    if name not in tools:
        raise GblupError("TOOL_NOT_FOUND", f"unknown tool {name}")
    validate_arguments(tools[name], arguments)
    if name == "gblup_inspect_inputs":
        return inspect_tool(base, arguments)
    if name == "gblup_fit":
        return fit_tool(base, arguments)
    if name == "gblup_export":
        return export_tool(base, arguments)
    raise GblupError("TOOL_NOT_FOUND", f"unknown tool {name}")


def result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
        "structuredContent": payload,
        "isError": False,
    }


def error_result(exc: GblupError) -> dict[str, Any]:
    payload = {"error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable}}
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "structuredContent": payload,
        "isError": True,
    }


def handle(request: dict[str, Any], base: Path) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested if isinstance(requested, str) and requested else "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "gblup", "version": "0.1.0"},
            },
        }
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS["tools"]}}
    if method == "tools/call":
        name = params.get("name") if isinstance(params, dict) else None
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "invalid tools/call"}}
        try:
            return {"jsonrpc": "2.0", "id": request_id, "result": result(call_tool(name, arguments, base))}
        except GblupError as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": error_result(exc)}
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": error_result(GblupError("INTERNAL_ERROR", f"{type(exc).__name__}: {exc}")),
            }
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main() -> int:
    parser = argparse.ArgumentParser(description="GBLUP MCP stdio server")
    parser.add_argument("--base-root", default=os.environ.get("GBLUP_MCP_INPUT_ROOT", "."))
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.run_root:
        os.environ["GBLUP_MCP_RUN_ROOT"] = args.run_root
    if args.version:
        print("gblup 0.1.0")
        return 0
    base = Path(args.base_root).expanduser().resolve()
    if not base.is_dir():
        print(f"base root is not a directory: {base}", file=sys.stderr)
        return 2
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
            continue
        response = handle(request, base)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
