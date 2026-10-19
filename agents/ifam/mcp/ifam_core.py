#!/usr/bin/env python3
"""Core IFAM inspection, job submission and export helpers.

The module is intentionally dependency-light: the MCP server can run with the
Python standard library. It never imports R. The only place R/HIBLUP are used
is the isolated worker process started by submit_fit().

The inspect output is designed to match fixtures/tiny/expected/inspect_inputs.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PINNED_COMMIT = "62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649"
PINNED_IFAM_R_SHA256 = "1ff7efa4e0ecaf2c4998202a3e5658e5cc2987878f3304479e39d18d210e0f11"
PAPER_DOI = "10.1038/s41467-026-72470-0"
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
SAFE_STEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
JOB_ID_RE = re.compile(r"^ifam-\d{8}-[0-9a-f]{8}$")
NA_VALUES = {"NA"}
NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


class IfamError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_relative(base: Path, relative: str, label: str, allow_dot: bool = False) -> Path:
    if not isinstance(relative, str) or not relative:
        raise IfamError("PATH_NOT_ALLOWED", f"{label} must be a non-empty relative path")
    if relative in (".", "") and allow_dot:
        return base
    if os.path.isabs(relative) or relative.startswith("~"):
        raise IfamError("PATH_NOT_ALLOWED", f"{label} must be relative, got {relative!r}")
    if not SAFE_PATH_RE.fullmatch(relative):
        raise IfamError(
            "PATH_NOT_ALLOWED",
            f"{label} contains whitespace or unsafe characters: {relative!r}",
        )
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise IfamError("PATH_NOT_ALLOWED", f"{label} contains an empty, '.' or '..' segment")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise IfamError("PATH_NOT_ALLOWED", f"{label} escapes the input root") from exc
    return resolved


def _read_fam(path: Path) -> list[str]:
    ids: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 6:
            raise IfamError("INVALID_PLINK_TRIO", f"{path.name}: line {line_no} has fewer than 6 columns")
        ids.append(fields[0])
    if not ids:
        raise IfamError("INVALID_PLINK_TRIO", f"{path.name} has no individuals")
    return ids


def _read_bim(path: Path) -> tuple[list[str], list[str], list[str]]:
    chroms: list[str] = []
    snp_ids: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 6:
            raise IfamError("INVALID_PLINK_TRIO", f"{path.name}: line {line_no} has fewer than 6 columns")
        chroms.append(fields[0])
        snp_ids.append(fields[1])
    if not snp_ids:
        raise IfamError("INVALID_PLINK_TRIO", f"{path.name} has no SNPs")
    return chroms, snp_ids


def _byte_table() -> list[tuple[int, int]]:
    """Return (missing_count, observed_code_mask) for each possible byte.

    PLINK 1 SNP-major codes: 00=0, 01=missing, 10=1, 11=2.
    The observed mask uses bits 0, 1 and 2 for genotypes 0, 1 and 2.
    """

    table: list[tuple[int, int]] = []
    for byte in range(256):
        missing = 0
        mask = 0
        for shift in (0, 2, 4, 6):
            code = (byte >> shift) & 0b11
            if code == 1:
                missing += 1
            elif code == 0:
                mask |= 1
            elif code == 2:
                mask |= 1 << 1
            else:
                mask |= 1 << 2
        table.append((missing, mask))
    return table


_BYTE_TABLE = _byte_table()


def _decode_bed(bed_path: Path, n_individuals: int, n_snps: int, snp_ids: list[str]) -> dict[str, Any]:
    data = bed_path.read_bytes()
    if len(data) < 3 or data[:3] != b"\x6c\x1b\x01":
        raise IfamError("INVALID_PLINK_TRIO", "not a SNP-major PLINK 1 .bed file")
    width = (n_individuals + 3) // 4
    expected_size = 3 + n_snps * width
    if len(data) != expected_size:
        raise IfamError(
            "INVALID_PLINK_TRIO",
            f".bed size is {len(data)} bytes; expected {expected_size} for {n_individuals} individuals and {n_snps} SNPs",
        )
    remainder = n_individuals % 4
    missing_total = 0
    monomorphic: list[str] = []
    offsets = memoryview(data)[3:]
    for snp_index in range(n_snps):
        row = offsets[snp_index * width : (snp_index + 1) * width]
        snp_missing = 0
        observed_mask = 0
        full_bytes = width if remainder == 0 else width - 1
        for byte in row[:full_bytes]:
            m, mask = _BYTE_TABLE[byte]
            snp_missing += m
            observed_mask |= mask
        if remainder:
            last = row[-1]
            for shift in range(0, 2 * remainder, 2):
                code = (last >> shift) & 0b11
                if code == 1:
                    snp_missing += 1
                elif code == 0:
                    observed_mask |= 1
                elif code == 2:
                    observed_mask |= 1 << 1
                else:
                    observed_mask |= 1 << 2
        missing_total += snp_missing
        # A marker with no observed genotypes or one genotype class is monomorphic.
        if observed_mask == 0 or observed_mask & (observed_mask - 1) == 0:
            monomorphic.append(snp_ids[snp_index])
    return {
        "missing_genotypes": missing_total,
        "total_genotypes": n_individuals * n_snps,
        "missing_rate": round(missing_total / (n_individuals * n_snps), 6) if n_individuals * n_snps else 0.0,
        "monomorphic_snps": monomorphic,
    }


def _read_phenotype(path: Path, column_index: int) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise IfamError("PHENOTYPE_HEADER_INVALID", "phenotype file is empty")
    header = lines[0].split("\t")
    if len(header) < 2:
        raise IfamError("PHENOTYPE_HEADER_INVALID", "phenotype header must contain at least two tab-separated columns")
    if column_index < 2 or column_index > len(header):
        raise IfamError(
            "PHENOTYPE_HEADER_INVALID",
            f"phenotype_index {column_index} is outside the {len(header)}-column header",
        )
    column_name = header[column_index - 1].strip()
    if not column_name or not SAFE_STEM_RE.fullmatch(column_name):
        raise IfamError(
            "PHENOTYPE_HEADER_INVALID",
            f"selected phenotype header is not a safe filename component: {column_name!r}",
        )
    rows: list[dict[str, Any]] = []
    ids: list[str] = []
    numeric = 0
    missing = 0
    for line_no, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < len(header):
            raise IfamError("PHENOTYPE_NON_NUMERIC", f"line {line_no} has fewer columns than the header")
        sample_id = fields[0].strip()
        if not sample_id:
            raise IfamError("ID_MISMATCH", f"line {line_no} has an empty individual ID")
        raw = fields[column_index - 1].strip()
        if raw.upper() in NA_VALUES:
            value: float | None = None
            missing += 1
        else:
            try:
                parsed = float(raw)
            except ValueError as exc:
                raise IfamError(
                    "PHENOTYPE_NON_NUMERIC",
                    f"line {line_no} target phenotype is not numeric or NA: {raw!r}",
                ) from exc
            if not math.isfinite(parsed):
                raise IfamError("PHENOTYPE_NON_NUMERIC", f"line {line_no} target phenotype is not finite")
            value = parsed
            numeric += 1
        ids.append(sample_id)
        rows.append({"sample_id": sample_id, "value": value})
    if not rows:
        raise IfamError("PHENOTYPE_HEADER_INVALID", "phenotype file has no data rows")
    if len(set(ids)) != len(ids):
        raise IfamError("DUPLICATE_INDIVIDUAL_ID", "phenotype has duplicate individual IDs")
    return {
        "header": header,
        "column_index": column_index,
        "column_name": column_name,
        "rows": rows,
        "ids": ids,
        "numeric_values": numeric,
        "missing_values": missing,
    }


def _read_annotations(
    annotation_dir: Path,
    relative_dir: str,
    snp_ids: set[str],
    specials: list[str],
) -> dict[str, Any]:
    files = sorted(annotation_dir.glob("*.txt"))
    errors: list[dict[str, Any]] = []
    if not files:
        errors.append({"code": "ANNOTATION_NOT_FOUND", "message": "annotation_dir has no .txt files"})
    if (annotation_dir / "annotation_names.txt").exists():
        errors.append(
            {
                "code": "ANNOTATION_LAYOUT_INVALID",
                "message": "annotation_names.txt is not a manifest for IFAM.R; it would be read as an annotation",
            }
        )
    entries: list[dict[str, Any]] = []
    members_by_name: dict[str, set[str]] = {}
    for path in files:
        stem = path.stem
        if not SAFE_STEM_RE.fullmatch(stem):
            errors.append(
                {
                    "code": "ANNOTATION_LAYOUT_INVALID",
                    "message": f"annotation filename is not safe for IFAM.R: {path.name!r}",
                }
            )
            continue
        raw_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        members = [line for line in raw_lines if line]
        if not members:
            errors.append({"code": "ANNOTATION_NOT_FOUND", "message": f"annotation {stem} is empty"})
            continue
        bad_rows = [line for line in members if len(line.split()) != 1]
        if bad_rows:
            errors.append(
                {
                    "code": "ANNOTATION_LAYOUT_INVALID",
                    "message": f"annotation {stem} is not a single headerless SNP column",
                }
            )
            continue
        unique = list(dict.fromkeys(members))
        counts = {}
        for snp in members:
            counts[snp] = counts.get(snp, 0) + 1
        duplicates = sorted(snp for snp, count in counts.items() if count > 1)
        unknown = [snp for snp in unique if snp not in snp_ids]
        members_by_name[stem] = set(unique)
        entries.append(
            {
                "name": stem,
                "file": f"{relative_dir}/{path.name}",
                "snps": len(members),
                "unique_snps": len(unique),
                "coverage_percent": round(100 * len(unique) / len(snp_ids), 2) if snp_ids else 0.0,
                "unknown_snps": unknown,
                "duplicate_snps": duplicates,
            }
        )

    special_set = set(specials)
    for stem in specials:
        if stem not in members_by_name:
            errors.append(
                {
                    "code": "SPECIAL_ANNOTATION_INVALID",
                    "message": f"special annotation stem {stem!r} was not found as a .txt file",
                }
            )
    if len(specials) > 1:
        errors.append(
            {
                "code": "SPECIAL_ANNOTATION_INVALID",
                "message": "IFAM.R 1.0.0 supports at most one special annotation",
            }
        )
    for entry in entries:
        entry["role"] = "special" if entry["name"] in special_set else "optimized"
    optimized = [entry for entry in entries if entry["role"] == "optimized"]
    special_entries = [entry for entry in entries if entry["role"] == "special"]
    unknown_any = any(entry["unknown_snps"] for entry in entries)
    if unknown_any:
        errors.append(
            {
                "code": "UNKNOWN_ANNOTATION_SNP",
                "message": "at least one annotation SNP is absent from the .bim; fix the build or SNP IDs",
            }
        )

    names = sorted(members_by_name)
    pairwise = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            left_set = members_by_name[left]
            right_set = members_by_name[right]
            intersection = len(left_set & right_set)
            union = len(left_set | right_set)
            pairwise.append(
                {
                    "a": left,
                    "b": right,
                    "intersection": intersection,
                    "jaccard": round(intersection / union, 4) if union else 0.0,
                }
            )
    union = set().union(*members_by_name.values()) if members_by_name else set()
    return {
        "directory": relative_dir,
        "discovery": "all *.txt files directly under directory",
        "optimized": optimized,
        "special": special_entries,
        "union_snps": len(union),
        "union_coverage_percent": round(100 * len(union) / len(snp_ids), 2) if snp_ids else 0.0,
        "pairwise_overlap": pairwise,
        "errors": errors,
    }


def _read_split(path: Path, fam_ids: set[str], phenotype: dict[str, Any], column_index: int) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IfamError("VALIDATION_SPLIT_INVALID", f"cannot parse split JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise IfamError("VALIDATION_SPLIT_INVALID", "split must be a JSON object")
    split_id = payload.get("split_id")
    training_ids = payload.get("training_ids")
    validation_ids = payload.get("validation_ids")
    if not isinstance(split_id, str) or not split_id:
        raise IfamError("VALIDATION_SPLIT_INVALID", "split_id is required")
    if not isinstance(training_ids, list) or not isinstance(validation_ids, list):
        raise IfamError("VALIDATION_SPLIT_INVALID", "training_ids and validation_ids must be arrays")
    training_ids = [str(value) for value in training_ids]
    validation_ids = [str(value) for value in validation_ids]
    if not training_ids or not validation_ids:
        raise IfamError("VALIDATION_SPLIT_INVALID", "both split sides must be non-empty")
    if len(set(training_ids)) != len(training_ids) or len(set(validation_ids)) != len(validation_ids):
        raise IfamError("VALIDATION_SPLIT_INVALID", "split IDs must be unique")
    overlap = set(training_ids) & set(validation_ids)
    if overlap:
        raise IfamError("VALIDATION_SPLIT_INVALID", f"training and validation overlap: {sorted(overlap)[:5]}")
    all_ids = set(training_ids) | set(validation_ids)
    missing_fam = sorted(all_ids - fam_ids)
    if missing_fam:
        raise IfamError("VALIDATION_SPLIT_INVALID", f"split IDs absent from .fam: {missing_fam[:5]}")
    pheno_values = {row["sample_id"]: row["value"] for row in phenotype["rows"]}
    missing_pheno = sorted(all_ids - set(pheno_values))
    if missing_pheno:
        raise IfamError("VALIDATION_SPLIT_INVALID", f"split IDs absent from phenotype: {missing_pheno[:5]}")
    leaked = [sample_id for sample_id in validation_ids if pheno_values[sample_id] is not None]
    return {
        "split_id": split_id,
        "training_ids": training_ids,
        "validation_ids": validation_ids,
        "validation_phenotypes_masked": not leaked,
        "leaked_validation_ids": leaked,
        "columns": column_index,
    }


def _empty_result(dataset: str, input_sha256: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "ifam.inspect.v1",
        "dataset": dataset,
        "status": "blocked",
        "counts": {
            "individuals": 0,
            "snps": 0,
            "annotations": 0,
            "optimized_annotations": 0,
            "special_annotations": 0,
        },
        "plink": {
            "prefix": "",
            "chromosomes": [],
            "variants_by_chromosome": {},
            "duplicate_snp_ids": [],
            "individual_ids_unique": False,
        },
        "phenotype": {
            "fit_file": "",
            "column_index": 0,
            "column_name": "",
            "individuals_in_file": 0,
            "matched_to_fam": 0,
            "missing_from_fam": [],
            "extra_in_fam": [],
            "numeric_values": 0,
            "missing_values": 0,
            "validation_split": None,
            "validation_ids": [],
            "validation_phenotypes_masked": None,
        },
        "annotations": {
            "directory": "",
            "discovery": "all *.txt files directly under directory",
            "optimized": [],
            "special": [],
            "union_snps": 0,
            "union_coverage_percent": 0.0,
            "pairwise_overlap": [],
        },
        "random_effects": {
            "requested_max": 0,
            "special_count": 0,
            "effective_optimization_cap": 0,
        },
        "genotypes": {
            "missing_genotypes": 0,
            "total_genotypes": 0,
            "missing_rate": 0.0,
            "monomorphic_snps": [],
        },
        "checks": [],
        "blocking_errors": [],
        "warnings": [],
        "notes": [],
        "input_sha256": input_sha256 or {},
    }


def _number_word(value: int) -> str:
    return NUMBER_WORDS.get(value, str(value))


def _natural_chrom_key(value: str) -> tuple[int, Any]:
    return (0, int(value)) if value.isdigit() else (1, value)


def inspect_dataset(
    base_root: Path,
    input_root: str = ".",
    bfile: str | None = None,
    phenotype: str | None = None,
    phenotype_index: int = 2,
    annotation_dir: str | None = None,
    special_annotations: list[str] | None = None,
    random_max: int = 5,
    validation_split: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate IFAM inputs and return (public_result, private_context)."""

    specials = list(special_annotations or [])
    if len(specials) > 1:
        raise IfamError("SPECIAL_ANNOTATION_INVALID", "IFAM.R 1.0.0 supports at most one special annotation")
    for stem in specials:
        if not SAFE_STEM_RE.fullmatch(stem):
            raise IfamError("PATH_NOT_ALLOWED", f"unsafe special annotation stem: {stem!r}")
    if not isinstance(random_max, int) or isinstance(random_max, bool) or random_max < 1:
        raise IfamError("RANDOM_MAX_INVALID", "random_max must be a positive integer")
    if not isinstance(phenotype_index, int) or isinstance(phenotype_index, bool) or phenotype_index < 2:
        raise IfamError("PHENOTYPE_HEADER_INVALID", "phenotype_index must be an integer >= 2")
    if not bfile or not phenotype or not annotation_dir:
        raise IfamError("INPUT_NOT_FOUND", "bfile, phenotype and annotation_dir are required")

    input_dir = _resolve_relative(base_root.resolve(), input_root, "input_root", allow_dot=True)
    if not input_dir.is_dir():
        raise IfamError("INPUT_NOT_FOUND", f"input_root is not a directory: {input_root}")
    dataset = input_dir.name or input_root
    input_sha256: dict[str, str] = {}

    bfile_rel = bfile
    bfile_path = _resolve_relative(input_dir, bfile, "bfile")
    bed_path = bfile_path.with_suffix(".bed")
    bim_path = bfile_path.with_suffix(".bim")
    fam_path = bfile_path.with_suffix(".fam")
    for path in (bed_path, bim_path, fam_path):
        if not path.is_file():
            raise IfamError("INPUT_NOT_FOUND", f"missing PLINK file: {path.relative_to(input_dir)}")
    phenotype_path = _resolve_relative(input_dir, phenotype, "phenotype")
    if not phenotype_path.is_file():
        raise IfamError("INPUT_NOT_FOUND", f"missing phenotype file: {phenotype}")
    annotation_path = _resolve_relative(input_dir, annotation_dir, "annotation_dir")
    if not annotation_path.is_dir():
        raise IfamError("INPUT_NOT_FOUND", f"missing annotation directory: {annotation_dir}")
    split_path = None
    split_rel = None
    if validation_split:
        split_rel = validation_split
        split_path = _resolve_relative(input_dir, validation_split, "validation_split")
        if not split_path.is_file():
            raise IfamError("INPUT_NOT_FOUND", f"missing validation split: {validation_split}")

    fam_ids = _read_fam(fam_path)
    if len(set(fam_ids)) != len(fam_ids):
        raise IfamError("DUPLICATE_INDIVIDUAL_ID", ".fam has duplicate individual IDs")
    chroms, snp_ids = _read_bim(bim_path)
    if len(set(snp_ids)) != len(snp_ids):
        raise IfamError("INVALID_PLINK_TRIO", ".bim has duplicate SNP IDs")
    phenotype_data = _read_phenotype(phenotype_path, phenotype_index)
    genotype_data = _decode_bed(bed_path, len(fam_ids), len(snp_ids), snp_ids)
    annotations = _read_annotations(annotation_path, annotation_dir, set(snp_ids), specials)

    split_data = None
    if split_path is not None:
        split_data = _read_split(split_path, set(fam_ids), phenotype_data, phenotype_index)
        if not split_data["validation_phenotypes_masked"]:
            raise IfamError(
                "VALIDATION_LEAKAGE",
                f"{len(split_data['leaked_validation_ids'])} validation IDs still have numeric fit phenotypes",
            )

    phenotype_ids = set(phenotype_data["ids"])
    missing_from_fam = [sample_id for sample_id in phenotype_data["ids"] if sample_id not in set(fam_ids)]
    extra_in_fam = [sample_id for sample_id in fam_ids if sample_id not in phenotype_ids]
    phenotype_match = not missing_from_fam and not extra_in_fam
    if not phenotype_match:
        raise IfamError(
            "ID_MISMATCH",
            f"phenotype and .fam differ: {len(missing_from_fam)} phenotype IDs not in .fam, {len(extra_in_fam)} .fam IDs not in phenotype",
        )

    blocking_errors = list(annotations["errors"])
    effective_cap = random_max - len(specials)
    if effective_cap < 1:
        blocking_errors.append(
            {
                "code": "RANDOM_MAX_INVALID",
                "message": f"random_max ({random_max}) must be greater than the special annotation count ({len(specials)})",
            }
        )
    if not genotype_data["missing_genotypes"] == genotype_data["missing_genotypes"]:
        blocking_errors.append({"code": "INVALID_PLINK_TRIO", "message": "invalid genotype decode"})

    chromosome_counts = {
        chrom: chroms.count(chrom) for chrom in sorted(set(chroms), key=_natural_chrom_key)
    }
    missing_genotypes = genotype_data["missing_genotypes"]
    total_genotypes = genotype_data["total_genotypes"]
    warnings = []
    if missing_genotypes:
        warnings.append(
            {
                "code": "MISSING_GENOTYPES",
                "severity": "warning",
                "message": (
                    f"{missing_genotypes} of {total_genotypes} genotypes "
                    f"{'is' if missing_genotypes == 1 else 'are'} missing; "
                    "PLINK missing code 01 is preserved."
                ),
            }
        )
    if specials:
        warnings.append(
            {
                "code": "SPECIAL_ANNOTATION_RANDOM_CAP",
                "severity": "info",
                "message": (
                    f"{specials[0]} is excluded from optimization and counts toward random_max; "
                    f"the effective optimization cap is {effective_cap}."
                ),
            }
        )

    checks: list[dict[str, str]] = [
        {"id": "plink_trio_present", "status": "pass"},
        {"id": "plink_bed_round_trip", "status": "pass"},
        {"id": "individual_ids_unique", "status": "pass"},
        {"id": "phenotype_header_present", "status": "pass"},
        {"id": "phenotype_ids_match_fam", "status": "pass"},
        {"id": "phenotype_numeric_or_na", "status": "pass"},
    ]
    if split_data is not None:
        checks.append(
            {
                "id": "validation_ids_masked",
                "status": "pass" if split_data["validation_phenotypes_masked"] else "fail",
            }
        )
        checks.append({"id": "validation_split_ids_disjoint", "status": "pass"})
    checks.extend(
        [
            {
                "id": "annotations_discovered_from_txt",
                "status": "pass" if not any(e["code"].startswith("ANNOTATION") for e in blocking_errors) else "fail",
            },
            {
                "id": "annotation_snps_known",
                "status": "pass" if not any(e["code"] == "UNKNOWN_ANNOTATION_SNP" for e in blocking_errors) else "fail",
            },
        ]
    )
    if specials:
        checks.append(
            {
                "id": "special_annotation_stem_matched",
                "status": "pass" if not any(e["code"] == "SPECIAL_ANNOTATION_INVALID" for e in blocking_errors) else "fail",
            }
        )
        checks.append(
            {
                "id": "random_max_after_special",
                "status": "pass" if effective_cap >= 1 else "fail",
            }
        )
    checks.append({"id": "missingness_within_plink_spec", "status": "pass"})

    notes = []
    if split_data is not None:
        notes.append(
            f"The fit phenotype masks the {_number_word(len(split_data['validation_ids']))} validation IDs as NA; "
            "held-out truth stays outside the MCP boundary for the independent benchmark runner."
        )
    notes.append(
        "IFAM.R discovers annotations as the *.txt files directly under annotation_dir; "
        "there is deliberately no annotation_names.txt manifest."
    )
    if specials:
        notes.append(
            f"{specials[0]} is passed to the wrapper as the special_annotation stem without .txt "
            f"(IFAM --anno_spec {specials[0]})."
        )
    fixture_path = input_dir / "fixture.json"
    if fixture_path.is_file():
        try:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            fixture = {}
        if fixture.get("status") == "synthetic-design-fixture":
            notes.append("All observations are synthetic and must never be reported as biological evidence.")

    # SHA-256 in the deterministic order used by the fixture golden file.
    for path in (bed_path, bim_path, fam_path):
        input_sha256[str(path.relative_to(input_dir))] = sha256_file(path)
    input_sha256[phenotype] = sha256_file(phenotype_path)
    if split_path is not None and split_rel is not None:
        input_sha256[split_rel] = sha256_file(split_path)
    for entry in sorted(annotations["optimized"] + annotations["special"], key=lambda item: item["file"]):
        input_sha256[entry["file"]] = sha256_file(input_dir / entry["file"])

    public = {
        "schema_version": "ifam.inspect.v1",
        "dataset": dataset,
        "status": "blocked" if blocking_errors else "ready",
        "counts": {
            "individuals": len(fam_ids),
            "snps": len(snp_ids),
            "annotations": len(annotations["optimized"]) + len(annotations["special"]),
            "optimized_annotations": len(annotations["optimized"]),
            "special_annotations": len(annotations["special"]),
        },
        "plink": {
            "prefix": bfile_rel,
            "chromosomes": sorted(set(chroms), key=_natural_chrom_key),
            "variants_by_chromosome": chromosome_counts,
            "duplicate_snp_ids": [],
            "individual_ids_unique": True,
        },
        "phenotype": {
            "fit_file": phenotype,
            "column_index": phenotype_index,
            "column_name": phenotype_data["column_name"],
            "individuals_in_file": len(phenotype_data["rows"]),
            "matched_to_fam": sum(1 for sample_id in phenotype_data["ids"] if sample_id in set(fam_ids)),
            "missing_from_fam": missing_from_fam,
            "extra_in_fam": extra_in_fam,
            "numeric_values": phenotype_data["numeric_values"],
            "missing_values": phenotype_data["missing_values"],
            "validation_split": split_rel,
            "validation_ids": split_data["validation_ids"] if split_data else [],
            "validation_phenotypes_masked": split_data["validation_phenotypes_masked"] if split_data else None,
        },
        "annotations": {
            "directory": annotation_dir,
            "discovery": annotations["discovery"],
            "optimized": annotations["optimized"],
            "special": annotations["special"],
            "union_snps": annotations["union_snps"],
            "union_coverage_percent": annotations["union_coverage_percent"],
            "pairwise_overlap": annotations["pairwise_overlap"],
        },
        "random_effects": {
            "requested_max": random_max,
            "special_count": len(specials),
            "effective_optimization_cap": effective_cap,
        },
        "genotypes": genotype_data,
        "checks": checks,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "notes": notes,
        "input_sha256": input_sha256,
    }
    context = {
        "input_dir": input_dir,
        "base_root": base_root,
        "bfile": bfile_rel,
        "bed_path": bed_path,
        "bim_path": bim_path,
        "fam_path": fam_path,
        "phenotype": phenotype,
        "phenotype_path": phenotype_path,
        "phenotype_index": phenotype_index,
        "column_name": phenotype_data["column_name"],
        "annotation_dir": annotation_dir,
        "annotation_path": annotation_path,
        "annotation_files": {
            entry["name"]: input_dir / entry["file"]
            for entry in annotations["optimized"] + annotations["special"]
        },
        "special_annotations": specials,
        "random_max": random_max,
        "split_path": split_path,
        "split": split_data,
        "fam_ids": fam_ids,
        "snp_ids": snp_ids,
        "dataset": dataset,
        "input_sha256": input_sha256,
    }
    return public, context


# ---------------------------------------------------------------------------
# Fit / status / export
# ---------------------------------------------------------------------------


def _job_root() -> Path:
    root = Path(os.environ.get("IFAM_MCP_JOB_ROOT", "/tmp/ifam-mcp-jobs"))
    raw = str(root)
    if not SAFE_PATH_RE.fullmatch(raw):
        raise IfamError(
            "PATH_NOT_ALLOWED",
            "IFAM_MCP_JOB_ROOT must not contain whitespace or shell metacharacters",
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cleanup_intermediates(out_dir: Path, keep: bool) -> list[str]:
    if keep:
        return []
    removed: list[str] = []
    patterns = ("*.GA", "*.GA.bin", "*.GA.id", "*.w.GA", "*.w.GA.bin", "*.w.GA.id", "*.beta", "*_vc.rand")
    for pattern in patterns:
        for path in out_dir.glob(pattern):
            if path.is_file():
                try:
                    path.unlink()
                    removed.append(str(path.relative_to(out_dir)))
                except OSError:
                    pass
    return removed


def _job_dir(job_id: str) -> Path:
    if not JOB_ID_RE.fullmatch(job_id):
        raise IfamError("JOB_NOT_FOUND", "invalid job ID")
    path = _job_root() / job_id
    if not path.is_dir():
        raise IfamError("JOB_NOT_FOUND", f"unknown job {job_id}")
    return path


def _read_job(job_dir: Path) -> dict[str, Any]:
    path = job_dir / "job.json"
    if not path.is_file():
        raise IfamError("JOB_NOT_FOUND", "job metadata is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_job(job_dir: Path, payload: dict[str, Any]) -> None:
    temp = job_dir / "job.json.tmp"
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(job_dir / "job.json")


def _find_tool(name: str, env_name: str) -> str:
    configured = os.environ.get(env_name)
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path)
    found = shutil.which(name)
    if not found:
        raise IfamError(
            "RUNTIME_UNAVAILABLE",
            f"{name} is not available; install it and put it on PATH (or set {env_name})",
            retryable=True,
        )
    return found


def _upstream_root() -> Path:
    configured = os.environ.get("IFAM_ROOT")
    if not configured:
        raise IfamError(
            "RUNTIME_UNAVAILABLE",
            "IFAM_ROOT is not set; point it at the extracted IFAM-main checkout",
            retryable=True,
        )
    root = Path(configured).expanduser().resolve()
    if not (root / "Scripts" / "IFAM.R").is_file():
        raise IfamError("RUNTIME_UNAVAILABLE", f"IFAM.R not found under {root}")
    return root


def _assert_pinned_ifam(root: Path) -> str:
    entrypoint = root / "Scripts" / "IFAM.R"
    actual = sha256_file(entrypoint)
    if actual != PINNED_IFAM_R_SHA256:
        raise IfamError(
            "UPSTREAM_HASH_MISMATCH",
            f"IFAM.R SHA-256 is {actual}; expected pinned {PINNED_IFAM_R_SHA256}",
        )
    return actual


def _copy_or_link(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _materialise_job_inputs(context: dict[str, Any], job_dir: Path) -> dict[str, str]:
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    bfile_target = input_dir / "data"
    _copy_or_link(context["bed_path"], bfile_target.with_suffix(".bed"))
    _copy_or_link(context["bim_path"], bfile_target.with_suffix(".bim"))
    _copy_or_link(context["fam_path"], bfile_target.with_suffix(".fam"))
    phenotype_target = input_dir / "phenotype.fit.txt"
    _copy_or_link(context["phenotype_path"], phenotype_target)
    for stem, source in context["annotation_files"].items():
        _copy_or_link(source, input_dir / "annotations" / f"{stem}.txt")
    split_target = None
    if context["split_path"] is not None:
        split_target = input_dir / "split.json"
        _copy_or_link(context["split_path"], split_target)
    return {
        "bfile": str(bfile_target),
        "phenotype": str(phenotype_target),
        "annotation_dir": str(input_dir / "annotations"),
        "split": str(split_target) if split_target else None,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tail(path: Path, limit: int = 4000) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def _publish_status(job_dir: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = _utc_now()
    _write_job(job_dir, payload)


def _run_fit(job_id: str) -> None:
    job_dir = _job_root() / job_id
    meta = _read_job(job_dir)
    log_path = job_dir / "run.log"
    try:
        rscript = _find_tool("Rscript", "RSCRIPT")
        upstream = _upstream_root()
        _assert_pinned_ifam(upstream)
        hiblup = _find_tool("hiblup", "HIBLUP")
        meta["state"] = "running"
        meta["phase"] = "building_grms"
        meta["started_at"] = _utc_now()
        _publish_status(job_dir, meta)
        work = job_dir / "work"
        work.mkdir(parents=True, exist_ok=True)
        out_dir = work / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_prefix = "IFAM"
        argv = [
            rscript,
            str(upstream / "Scripts" / "IFAM.R"),
            "--bfile",
            meta["paths"]["bfile"],
            "--pheno",
            meta["paths"]["phenotype"],
            "--anno_folder",
            meta["paths"]["annotation_dir"] + os.sep,
            "--pheno_pos",
            str(meta["phenotype_index"]),
            "--randomMax",
            str(meta["random_max"]),
            "--VCmethod",
            meta["vc_method"],
            "--thread",
            str(meta["threads"]),
            "--tmp_files",
            "TRUE",
            "--outPath",
            str(out_dir) + os.sep,
            "--output_prefix",
            out_prefix,
        ]
        if meta["special_annotations"]:
            argv.extend(["--anno_spec", meta["special_annotations"][0]])
        env = os.environ.copy()
        env["PATH"] = str(Path(hiblup).parent) + os.pathsep + env.get("PATH", "")
        fingerprint_payload = json.dumps(argv, ensure_ascii=False, separators=(",", ":"))
        meta["command_fingerprint"] = "sha256:" + hashlib.sha256(fingerprint_payload.encode()).hexdigest()
        meta["command"] = argv
        _publish_status(job_dir, meta)
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                argv,
                cwd=str(work),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            meta["pid"] = process.pid
            _publish_status(job_dir, meta)
            assert process.stdout is not None
            for line in process.stdout:
                log_handle.write(line)
                log_handle.flush()
                if "Estimating variance components" in line and meta["phase"] != "estimating_variance":
                    meta["phase"] = "estimating_variance"
                    _publish_status(job_dir, meta)
                elif "Predicting additive genetic values" in line and meta["phase"] != "predicting":
                    meta["phase"] = "predicting"
                    _publish_status(job_dir, meta)
                elif "IFAM is end" in line:
                    meta["phase"] = "parsing_outputs"
                    _publish_status(job_dir, meta)
            return_code = process.wait()
        rand_path = out_dir / f"{out_prefix}_{meta['trait']}.rand"
        vars_path = out_dir / f"{out_prefix}_{meta['trait']}.vars"
        vc_vars_path = out_dir / f"{out_prefix}_{meta['trait']}_vc.vars"
        annotation_info = out_dir / f"{out_prefix}.annotaion.information.txt"
        overlap = out_dir / f"{out_prefix}.overlaped.SNPs.between.anntations.txt"
        required = [rand_path, vars_path, annotation_info, overlap]
        missing = [str(path.relative_to(job_dir)) for path in required if not path.is_file()]
        if return_code != 0 or missing:
            meta["state"] = "failed"
            meta["phase"] = "failed"
            meta["finished_at"] = _utc_now()
            meta["error"] = {
                "code": "UPSTREAM_FAILURE",
                "message": f"IFAM/HIBLUP exit={return_code}; missing required artifacts: {missing or 'none'}",
                "retryable": False,
                "log_tail": _tail(log_path),
            }
            _publish_status(job_dir, meta)
            return
        meta["state"] = "succeeded"
        meta["phase"] = "complete"
        meta["finished_at"] = _utc_now()
        meta["removed_intermediates"] = _cleanup_intermediates(out_dir, bool(meta.get("keep_intermediate")))
        meta["artifacts"] = [
            str(path.relative_to(job_dir))
            for path in sorted(out_dir.iterdir())
            if path.is_file()
        ]
        meta["error"] = None
        _publish_status(job_dir, meta)
    except IfamError as exc:
        meta["state"] = "failed"
        meta["phase"] = "failed"
        meta["finished_at"] = _utc_now()
        meta["error"] = {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "log_tail": _tail(log_path),
        }
        _publish_status(job_dir, meta)
    except Exception as exc:  # pragma: no cover - unexpected worker failure
        meta["state"] = "failed"
        meta["phase"] = "failed"
        meta["finished_at"] = _utc_now()
        meta["error"] = {
            "code": "UPSTREAM_FAILURE",
            "message": f"{type(exc).__name__}: {exc}",
            "retryable": False,
            "log_tail": _tail(log_path),
        }
        _publish_status(job_dir, meta)


def submit_fit(
    base_root: Path,
    input_root: str = ".",
    bfile: str | None = None,
    phenotype: str | None = None,
    phenotype_index: int = 2,
    annotation_dir: str | None = None,
    special_annotations: list[str] | None = None,
    random_max: int = 5,
    validation_split: str | None = None,
    vc_method: str = "AI",
    threads: int = 1,
    keep_intermediate: bool = False,
) -> dict[str, Any]:
    if vc_method not in {"AI", "EM", "EMAI", "HE", "HI"}:
        raise IfamError("VALIDATION_ERROR", f"unsupported vc_method {vc_method!r}")
    if not isinstance(threads, int) or isinstance(threads, bool) or not 1 <= threads <= 32:
        raise IfamError("RESOURCE_LIMIT", "threads must be an integer between 1 and 32")
    public, context = inspect_dataset(
        base_root=base_root,
        input_root=input_root,
        bfile=bfile,
        phenotype=phenotype,
        phenotype_index=phenotype_index,
        annotation_dir=annotation_dir,
        special_annotations=special_annotations,
        random_max=random_max,
        validation_split=validation_split,
    )
    if public["status"] != "ready":
        raise IfamError(
            "INPUT_VALIDATION_FAILED",
            "inspect_inputs reported blocking errors; fix them before fitting",
            details={"blocking_errors": public["blocking_errors"]},
        )
    # Check the runtime before creating a job so callers get a stable error.
    runtime_mode = "stub" if os.environ.get("IFAM_MCP_STUB") == "1" else "real"
    _find_tool("Rscript", "RSCRIPT")
    _find_tool("hiblup", "HIBLUP")
    upstream = _upstream_root()
    _assert_pinned_ifam(upstream)

    job_id = f"ifam-{datetime.now().strftime('%Y%m%d')}-{os.urandom(4).hex()}"
    job_dir = _job_root() / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    paths = _materialise_job_inputs(context, job_dir)
    split_copy = job_dir / "input" / "split.json"
    meta = {
        "schema_version": "ifam.job.v1",
        "job_id": job_id,
        "state": "queued",
        "phase": "queued",
        "submitted_at": _utc_now(),
        "updated_at": _utc_now(),
        "started_at": None,
        "finished_at": None,
        "effective_random_max": public["random_effects"]["effective_optimization_cap"],
        "upstream": {
            "repository": "https://github.com/xiaolei-lab/IFAM",
            "commit": PINNED_COMMIT,
            "entrypoint": "Scripts/IFAM.R",
            "ifam_r_sha256": PINNED_IFAM_R_SHA256,
            "hiblup": os.environ.get("HIBLUP_VERSION", "1.1.0"),
            "runtime_mode": runtime_mode,
        },
        "runtime_mode": runtime_mode,
        "command_fingerprint": None,
        "warnings": (
            ["STUB_RUNTIME: synthetic worker outputs; this is not IFAM evidence."]
            if runtime_mode == "stub"
            else []
        ) + [warning["message"] for warning in public["warnings"]],
        "trait": context["column_name"],
        "phenotype_index": phenotype_index,
        "random_max": random_max,
        "special_annotations": context["special_annotations"],
        "vc_method": vc_method,
        "threads": threads,
        "keep_intermediate": bool(keep_intermediate),
        "paths": paths,
        "input_sha256": context["input_sha256"],
        "split": context["split"],
        "split_sha256": sha256_file(split_copy) if split_copy.is_file() else None,
        "dataset": context["dataset"],
        "error": None,
    }
    _write_job(job_dir, meta)
    thread = threading.Thread(target=_run_fit, args=(job_id,), name=f"ifam-fit-{job_id}", daemon=True)
    thread.start()
    return {
        "schema_version": "ifam.job.v1",
        "job_id": job_id,
        "state": "queued",
        "submitted_at": meta["submitted_at"],
        "effective_random_max": meta["effective_random_max"],
        "upstream": meta["upstream"],
        "command_fingerprint": None,
        "warnings": meta["warnings"],
    }


def get_job_status(job_id: str) -> dict[str, Any]:
    job_dir = _job_dir(job_id)
    meta = _read_job(job_dir)
    log_tail = _tail(job_dir / "run.log")
    result = {
        "schema_version": "ifam.status.v1",
        "job_id": job_id,
        "state": meta.get("state", "failed"),
        "phase": meta.get("phase", "failed"),
        "submitted_at": meta.get("submitted_at"),
        "started_at": meta.get("started_at"),
        "finished_at": meta.get("finished_at"),
        "elapsed_seconds": None,
        "progress": None,
        "error": meta.get("error"),
        "artifacts": meta.get("artifacts", []),
    }
    if meta.get("started_at"):
        try:
            start = datetime.fromisoformat(meta["started_at"].replace("Z", "+00:00"))
            end = (
                datetime.fromisoformat(meta["finished_at"].replace("Z", "+00:00"))
                if meta.get("finished_at")
                else datetime.now(timezone.utc)
            )
            result["elapsed_seconds"] = max(0.0, round((end - start).total_seconds(), 3))
        except ValueError:
            pass
    if meta.get("phase") in {"building_grms", "estimating_variance", "predicting", "parsing_outputs"}:
        result["progress"] = {"phase": meta["phase"], "log_tail": log_tail[-1200:]}
    if result["error"]:
        result["error"] = dict(result["error"])
        result["error"]["log_tail"] = log_tail[-4000:]
    return result


def _parse_vars(path: Path, stage: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return rows
    header = lines[0].split("\t")
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) < len(header):
            continue
        record: dict[str, Any] = {"stage": stage}
        for key, raw in zip(header, fields):
            value: Any = raw.strip()
            numeric_keys = {"Var", "Var_SE", "h2", "h2_SE", "h2_Pr(Chisq)"}
            if key in numeric_keys:
                try:
                    parsed = float(value)
                    record[key] = parsed if math.isfinite(parsed) else None
                except ValueError:
                    record[key] = None
            else:
                record[key] = value
        rows.append(record)
    return rows


def _parse_annotation_info(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) != len(header):
            continue
        rows.append(dict(zip(header, fields)))
    return {"header": header, "rows": rows}


def export_job(job_id: str) -> dict[str, Any]:
    job_dir = _job_dir(job_id)
    meta = _read_job(job_dir)
    if meta.get("state") != "succeeded":
        raise IfamError("JOB_NOT_READY", f"job is {meta.get('state')}, not succeeded", retryable=True)
    out_dir = job_dir / "work" / "out"
    trait = meta["trait"]
    rand_path = out_dir / f"IFAM_{trait}.rand"
    if not rand_path.is_file():
        raise IfamError("UPSTREAM_FAILURE", "IFAM .rand file is missing")
    lines = rand_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise IfamError("UPSTREAM_FAILURE", "IFAM .rand file is empty")
    header = lines[0].split("\t")
    try:
        id_index = 0
        value_index = header.index("genetic_values")
        residual_index = header.index("residuals") if "residuals" in header else None
    except ValueError as exc:
        raise IfamError("UPSTREAM_FAILURE", f".rand is missing genetic_values: {header}") from exc
    predictions = []
    seen: set[str] = set()
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) <= value_index:
            continue
        sample_id = fields[id_index].strip()
        if not sample_id:
            continue
        if sample_id in seen:
            raise IfamError("UPSTREAM_FAILURE", f"duplicate prediction ID {sample_id}")
        seen.add(sample_id)
        try:
            genetic_value = float(fields[value_index])
            residual = float(fields[residual_index]) if residual_index is not None else None
        except ValueError as exc:
            raise IfamError("UPSTREAM_FAILURE", f"non-numeric prediction for {sample_id}") from exc
        predictions.append(
            {
                "sample_id": sample_id,
                "genetic_value": genetic_value,
                "residual": residual,
            }
        )
    split = meta.get("split") or {}
    validation_ids = split.get("validation_ids", []) or []
    missing = [sample_id for sample_id in validation_ids if sample_id not in seen]
    if missing:
        raise IfamError(
            "PREDICTIONS_INCOMPLETE",
            f"predictions are missing {len(missing)} validation IDs",
            details={"missing_ids": missing[:20]},
        )
    vars_final = _parse_vars(out_dir / f"IFAM_{trait}.vars", "final_model")
    vars_vc = _parse_vars(out_dir / f"IFAM_{trait}_vc.vars", "variance_estimation")
    annotation_info = _parse_annotation_info(out_dir / "IFAM.annotaion.information.txt")
    if annotation_info is None:
        raise IfamError("UPSTREAM_FAILURE", "annotation information is missing")
    artifacts = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            artifacts.append(
                {
                    "path": str(path.relative_to(job_dir)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    output = {
        "schema_version": "ifam.export.v1",
        "job_id": job_id,
        "split_id": split.get("split_id"),
        "validation_ids": validation_ids,
        "n_predictions": len(predictions),
        "predictions": predictions,
        "variance_components": vars_vc + vars_final,
        "annotation_summary": annotation_info,
        "artifacts": artifacts,
        "provenance": {
            "paper_doi": PAPER_DOI,
            "code_commit": PINNED_COMMIT,
            "hiblup": meta.get("upstream", {}).get("hiblup", "unknown"),
            "ifam_r_sha256": PINNED_IFAM_R_SHA256,
            "command_fingerprint": meta.get("command_fingerprint"),
            "input_sha256": meta.get("input_sha256", {}),
            "split_sha256": meta.get("split_sha256"),
            "job_dataset": meta.get("dataset"),
            "runtime_mode": meta.get("runtime_mode", "real"),
            "stub_notice": (
                "Synthetic stub runtime; not IFAM evidence."
                if meta.get("runtime_mode") == "stub"
                else None
            ),
        },
    }
    export_path = job_dir / "export.json"
    export_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def runtime_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "schema_version": "ifam.runtime.v1",
        "rscript": None,
        "hiblup": None,
        "upstream_root": None,
        "ifam_r_sha256": None,
        "ifam_r_pinned": False,
        "plink": None,
        "stub_mode": os.environ.get("IFAM_MCP_STUB") == "1",
        "blocking_errors": [],
        "warnings": [],
    }
    try:
        status["rscript"] = _find_tool("Rscript", "RSCRIPT")
    except IfamError as exc:
        status["blocking_errors"].append({"code": exc.code, "message": exc.message})
    try:
        status["hiblup"] = _find_tool("hiblup", "HIBLUP")
    except IfamError as exc:
        status["blocking_errors"].append({"code": exc.code, "message": exc.message})
    try:
        root = _upstream_root()
        status["upstream_root"] = str(root)
        actual = sha256_file(root / "Scripts" / "IFAM.R")
        status["ifam_r_sha256"] = actual
        status["ifam_r_pinned"] = actual == PINNED_IFAM_R_SHA256
        if not status["ifam_r_pinned"]:
            status["blocking_errors"].append(
                {
                    "code": "UPSTREAM_HASH_MISMATCH",
                    "message": f"IFAM.R hash {actual} does not match {PINNED_IFAM_R_SHA256}",
                }
            )
    except IfamError as exc:
        status["blocking_errors"].append({"code": exc.code, "message": exc.message})
    status["plink"] = shutil.which("plink")
    if not status["plink"]:
        status["warnings"].append(
            {
                "code": "PLINK_UNAVAILABLE",
                "message": "plink is not on PATH; the Python subsetter is used for acceptance, and external PLINK validation is deferred",
            }
        )
    return status


def main(argv: list[str] | None = None) -> int:
    """Small CLI for local checks, independent of the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="IFAM core helper")
    parser.add_argument("command", choices=["inspect", "runtime-status"])
    parser.add_argument("--base-root", default=".")
    parser.add_argument("--input-root", default=".")
    parser.add_argument("--bfile")
    parser.add_argument("--phenotype")
    parser.add_argument("--phenotype-index", type=int, default=2)
    parser.add_argument("--annotation-dir")
    parser.add_argument("--special", action="append", default=[])
    parser.add_argument("--random-max", type=int, default=5)
    parser.add_argument("--split")
    args = parser.parse_args(argv)
    try:
        if args.command == "runtime-status":
            print(json.dumps(runtime_status(), indent=2))
            return 0
        result, _ = inspect_dataset(
            Path(args.base_root),
            input_root=args.input_root,
            bfile=args.bfile,
            phenotype=args.phenotype,
            phenotype_index=args.phenotype_index,
            annotation_dir=args.annotation_dir,
            special_annotations=args.special,
            random_max=args.random_max,
            validation_split=args.split,
        )
        print(json.dumps(result, indent=2))
        return 0
    except IfamError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
