#!/usr/bin/env python3
"""Generate the deterministic synthetic fixture for the IFAM MCP contract.

This fixture mirrors the documented IFAM input formats. It contains no
human, pig, rice, or other real observations. It is intended for schema,
validation, and plumbing tests only, not for scientific findings.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 20261018

INDIVIDUALS = [f"I{i:02d}" for i in range(1, 13)]
SNPS = [f"snp{i:02d}" for i in range(1, 25)]
CHROMOSOMES = ["1"] * 16 + ["2"] * 8
POSITIONS = [1000 * (i + 1) for i in range(24)]

ANNOTATIONS = {
    "enhancer": SNPS[0:8],
    "promoter": SNPS[4:12],
    "tfbs": SNPS[8:16],
    "trait_snps": SNPS[17:21],
}
SPECIAL_ANNOTATIONS = ["trait_snps"]
VALIDATION_IDS = INDIVIDUALS[8:]
TRAINING_IDS = INDIVIDUALS[:8]

TRUTH = {
    "I01": 101.200,
    "I02": 104.800,
    "I03": 98.600,
    "I04": 103.100,
    "I05": 100.400,
    "I06": 106.300,
    "I07": 97.900,
    "I08": 102.700,
    "I09": 104.100,
    "I10": 99.300,
    "I11": 105.600,
    "I12": 96.800,
}

# Allele-2 frequencies are fixed so regeneration does not depend on RNG
# implementation details beyond random.Random(seed).
ALLELE2_FREQUENCY = [
    0.15, 0.25, 0.35, 0.20, 0.30, 0.40, 0.10, 0.45,
    0.22, 0.32, 0.42, 0.18, 0.28, 0.38, 0.48, 0.12,
    0.24, 0.34, 0.44, 0.16, 0.26, 0.36, 0.46, 0.14,
]


def build_genotypes() -> dict[str, list[int | None]]:
    rng = random.Random(SEED)
    genotypes: dict[str, list[int | None]] = {}

    for snp, allele2_frequency in zip(SNPS, ALLELE2_FREQUENCY):
        p = allele2_frequency
        row: list[int | None] = []
        for _ in INDIVIDUALS:
            draw = rng.random()
            if draw < (1 - p) ** 2:
                row.append(0)
            elif draw < 1 - p**2:
                row.append(1)
            else:
                row.append(2)

        # Keep every marker polymorphic.
        if len(set(row)) == 1:
            row[SNPS.index(snp) % len(INDIVIDUALS)] = 2 if row[0] == 0 else 0

        genotypes[snp] = row

    # A single missing genotype exercises PLINK's missing code (01).
    genotypes["snp07"][INDIVIDUALS.index("I12")] = None
    for snp in SNPS:
        observed = {genotype for genotype in genotypes[snp] if genotype is not None}
        if len(observed) < 2:
            raise AssertionError(f"{snp} became monomorphic after masking")
    return genotypes


def pack_bed(genotypes: dict[str, list[int | None]]) -> bytes:
    payload = bytearray()
    codes = {0: 0b00, 1: 0b10, 2: 0b11, None: 0b01}
    for snp in SNPS:
        payload.extend(_pack_snp(genotypes[snp], codes))
    return b"\x6c\x1b\x01" + bytes(payload)


def _pack_snp(row: list[int | None], codes: dict[int | None, int]) -> bytes:
    packed = bytearray((len(row) + 3) // 4)
    for i, genotype in enumerate(row):
        packed[i // 4] |= codes[genotype] << (2 * (i % 4))
    return bytes(packed)


def unpack_bed(path: Path) -> dict[str, list[int | None]]:
    data = path.read_bytes()
    if data[:3] != b"\x6c\x1b\x01":
        raise AssertionError("Not a SNP-major PLINK 1 .bed file")
    codes = {0b00: 0, 0b10: 1, 0b11: 2, 0b01: None}
    width = (len(INDIVIDUALS) + 3) // 4
    genotypes: dict[str, list[int | None]] = {}
    offset = 3
    for snp in SNPS:
        row = []
        for i in range(len(INDIVIDUALS)):
            byte = data[offset + i // 4]
            row.append(codes[(byte >> (2 * (i % 4))) & 0b11])
        genotypes[snp] = row
        offset += width
    if offset != len(data):
        raise AssertionError("Unexpected trailing bytes in .bed")
    return genotypes


def write_plink(genotypes: dict[str, list[int | None]]) -> None:
    geno_dir = ROOT / "geno"
    geno_dir.mkdir(parents=True, exist_ok=True)

    bed = pack_bed(genotypes)
    (geno_dir / "tiny.bed").write_bytes(bed)
    assert unpack_bed(geno_dir / "tiny.bed") == genotypes

    bim_lines = [
        f"{chrom}\t{snp}\t0\t{position}\tA\tG"
        for chrom, snp, position in zip(CHROMOSOMES, SNPS, POSITIONS)
    ]
    (geno_dir / "tiny.bim").write_text("\n".join(bim_lines) + "\n", encoding="utf-8")

    fam_lines = [f"{individual}\t{individual}\t0\t0\t0\t-9" for individual in INDIVIDUALS]
    (geno_dir / "tiny.fam").write_text("\n".join(fam_lines) + "\n", encoding="utf-8")


def write_phenotypes() -> None:
    pheno_dir = ROOT / "pheno"
    pheno_dir.mkdir(parents=True, exist_ok=True)

    truth_lines = ["ID\ttrait"] + [
        f"{individual}\t{TRUTH[individual]:.3f}" for individual in INDIVIDUALS
    ]
    (pheno_dir / "phenotype.truth.txt").write_text(
        "\n".join(truth_lines) + "\n", encoding="utf-8"
    )

    fit_lines = ["ID\ttrait"]
    for individual in INDIVIDUALS:
        value = "NA" if individual in VALIDATION_IDS else f"{TRUTH[individual]:.3f}"
        fit_lines.append(f"{individual}\t{value}")
    (pheno_dir / "phenotype.fit.txt").write_text(
        "\n".join(fit_lines) + "\n", encoding="utf-8"
    )


def write_annotations() -> None:
    anno_dir = ROOT / "annotations"
    anno_dir.mkdir(parents=True, exist_ok=True)

    for name, members in ANNOTATIONS.items():
        (anno_dir / f"{name}.txt").write_text("\n".join(members) + "\n", encoding="utf-8")

    # IFAM.R auto-discovers every *.txt in --anno_folder. A manifest file such
    # as annotation_names.txt would therefore be read as a bogus annotation.
    stale_manifest = anno_dir / "annotation_names.txt"
    if stale_manifest.exists():
        stale_manifest.unlink()


def write_split() -> None:
    split_dir = ROOT / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    split = {
        "schema_version": "ifam.split.v1",
        "split_id": "repeat-1",
        "seed": SEED,
        "training_ids": TRAINING_IDS,
        "validation_ids": VALIDATION_IDS,
    }
    (split_dir / "repeat-1.json").write_text(
        json.dumps(split, indent=2) + "\n", encoding="utf-8"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def annotation_summary() -> list[dict]:
    entries = []
    for name, members in ANNOTATIONS.items():
        unique = list(dict.fromkeys(members))
        entries.append(
            {
                "name": name,
                "file": f"annotations/{name}.txt",
                "role": "special" if name in SPECIAL_ANNOTATIONS else "optimized",
                "snps": len(members),
                "unique_snps": len(unique),
                "coverage_percent": round(100 * len(unique) / len(SNPS), 2),
                "unknown_snps": [snp for snp in unique if snp not in SNPS],
                "duplicate_snps": sorted({snp for snp in members if members.count(snp) > 1}),
            }
        )
    return entries


def pairwise_overlap() -> list[dict]:
    names = list(ANNOTATIONS)
    result = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            left_set = set(ANNOTATIONS[left])
            right_set = set(ANNOTATIONS[right])
            intersection = len(left_set & right_set)
            union = len(left_set | right_set)
            result.append(
                {
                    "a": left,
                    "b": right,
                    "intersection": intersection,
                    "jaccard": round(intersection / union, 4),
                }
            )
    return result


def write_expected(genotypes: dict[str, list[int | None]]) -> None:
    expected_dir = ROOT / "expected"
    expected_dir.mkdir(parents=True, exist_ok=True)

    annotation_entries = annotation_summary()
    union = set().union(*(set(members) for members in ANNOTATIONS.values()))
    missing = sum(
        1 for snp in SNPS for genotype in genotypes[snp] if genotype is None
    )
    monomorphic = [
        snp for snp in SNPS if len({g for g in genotypes[snp] if g is not None}) == 1
    ]

    input_paths = [
        ROOT / "geno" / "tiny.bed",
        ROOT / "geno" / "tiny.bim",
        ROOT / "geno" / "tiny.fam",
        ROOT / "pheno" / "phenotype.fit.txt",
        ROOT / "splits" / "repeat-1.json",
        *[ROOT / "annotations" / f"{name}.txt" for name in ANNOTATIONS],
    ]

    expected = {
        "schema_version": "ifam.inspect.v1",
        "dataset": "tiny",
        "status": "ready",
        "counts": {
            "individuals": len(INDIVIDUALS),
            "snps": len(SNPS),
            "annotations": len(ANNOTATIONS),
            "optimized_annotations": len(ANNOTATIONS) - len(SPECIAL_ANNOTATIONS),
            "special_annotations": len(SPECIAL_ANNOTATIONS),
        },
        "plink": {
            "prefix": "geno/tiny",
            "chromosomes": sorted(set(CHROMOSOMES)),
            "variants_by_chromosome": {
                chrom: CHROMOSOMES.count(chrom) for chrom in sorted(set(CHROMOSOMES))
            },
            "duplicate_snp_ids": [],
            "individual_ids_unique": True,
        },
        "phenotype": {
            "fit_file": "pheno/phenotype.fit.txt",
            "column_index": 2,
            "column_name": "trait",
            "individuals_in_file": len(INDIVIDUALS),
            "matched_to_fam": len(INDIVIDUALS),
            "missing_from_fam": [],
            "extra_in_fam": [],
            "numeric_values": len(TRAINING_IDS),
            "missing_values": len(VALIDATION_IDS),
            "validation_split": "splits/repeat-1.json",
            "validation_ids": VALIDATION_IDS,
            "validation_phenotypes_masked": True,
        },
        "annotations": {
            "directory": "annotations",
            "discovery": "all *.txt files directly under directory",
            "optimized": [entry for entry in annotation_entries if entry["role"] == "optimized"],
            "special": [entry for entry in annotation_entries if entry["role"] == "special"],
            "union_snps": len(union),
            "union_coverage_percent": round(100 * len(union) / len(SNPS), 2),
            "pairwise_overlap": pairwise_overlap(),
        },
        "random_effects": {
            "requested_max": 5,
            "special_count": len(SPECIAL_ANNOTATIONS),
            "effective_optimization_cap": 5 - len(SPECIAL_ANNOTATIONS),
        },
        "genotypes": {
            "missing_genotypes": missing,
            "total_genotypes": len(SNPS) * len(INDIVIDUALS),
            "missing_rate": round(missing / (len(SNPS) * len(INDIVIDUALS)), 6),
            "monomorphic_snps": monomorphic,
        },
        "checks": [
            {"id": "plink_trio_present", "status": "pass"},
            {"id": "plink_bed_round_trip", "status": "pass"},
            {"id": "individual_ids_unique", "status": "pass"},
            {"id": "phenotype_header_present", "status": "pass"},
            {"id": "phenotype_ids_match_fam", "status": "pass"},
            {"id": "phenotype_numeric_or_na", "status": "pass"},
            {"id": "validation_ids_masked", "status": "pass"},
            {"id": "validation_split_ids_disjoint", "status": "pass"},
            {"id": "annotations_discovered_from_txt", "status": "pass"},
            {"id": "annotation_snps_known", "status": "pass"},
            {"id": "special_annotation_stem_matched", "status": "pass"},
            {"id": "random_max_after_special", "status": "pass"},
            {"id": "missingness_within_plink_spec", "status": "pass"},
        ],
        "blocking_errors": [],
        "warnings": [
            {
                "code": "MISSING_GENOTYPES",
                "severity": "warning",
                "message": "1 of 288 genotypes is missing; PLINK missing code 01 is preserved.",
            },
            {
                "code": "SPECIAL_ANNOTATION_RANDOM_CAP",
                "severity": "info",
                "message": "trait_snps is excluded from optimization and counts toward random_max; the effective optimization cap is 4.",
            },
        ],
        "notes": [
            "The fit phenotype masks the four validation IDs as NA; held-out truth stays outside the MCP boundary for the independent benchmark runner.",
            "IFAM.R discovers annotations as the *.txt files directly under annotation_dir; there is deliberately no annotation_names.txt manifest.",
            "trait_snps is passed to the wrapper as the special_annotation stem without .txt (IFAM --anno_spec trait_snps).",
            "All observations are synthetic and must never be reported as biological evidence.",
        ],
        "input_sha256": {relative(path): sha256(path) for path in input_paths},
    }

    (expected_dir / "inspect_inputs.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8"
    )


def write_fixture_manifest(expected_path: Path) -> None:
    files = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path != ROOT / "fixture.json"
        and "__pycache__" not in path.parts
    )
    manifest = {
        "schema_version": "ifam.fixture.v1",
        "name": "tiny",
        "status": "synthetic-design-fixture",
        "purpose": "Exercise the IFAM MCP contract and inspection logic without real or restricted data.",
        "not_for": "Scientific claims, benchmark evidence, or model ranking.",
        "seed": SEED,
        "generator": {
            "path": "generate.py",
            "sha256": sha256(ROOT / "generate.py"),
        },
        "counts": {
            "individuals": len(INDIVIDUALS),
            "snps": len(SNPS),
            "annotations": len(ANNOTATIONS),
            "training_ids": len(TRAINING_IDS),
            "validation_ids": len(VALIDATION_IDS),
        },
        "upstream": {
            "repository": "https://github.com/xiaolei-lab/IFAM",
            "commit": "62f8e4cd8ee53d70b3324ec5cd40d3f2ffbf7649",
            "archive_sha256": "b66f1a6d9b01115d955552a1252a4ea3d22ad25b335fce1fcf8b41ba8a91bd2b",
            "inspected_on": "2026-10-18",
            "executed": False,
            "note": "Format calibrated against IFAM.R 1.0.0 (sha256 1ff7efa4e0ecaf2c4998202a3e5658e5cc2987878f3304479e39d18d210e0f11); not executed through IFAM.R or HIBLUP v1.1.0.",
        },
        "expected": relative(expected_path),
        "files_sha256": {relative(path): sha256(path) for path in files},
    }
    (ROOT / "fixture.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    genotypes = build_genotypes()
    write_plink(genotypes)
    write_phenotypes()
    write_annotations()
    write_split()
    write_expected(genotypes)
    write_fixture_manifest(ROOT / "expected" / "inspect_inputs.json")
    print(f"Wrote synthetic IFAM fixture to {ROOT}")
    print(f"Individuals: {len(INDIVIDUALS)}; SNPs: {len(SNPS)}; annotations: {len(ANNOTATIONS)}")


if __name__ == "__main__":
    main()
