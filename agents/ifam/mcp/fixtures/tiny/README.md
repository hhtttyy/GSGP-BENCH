# IFAM tiny fixture

Synthetic input data for testing the draft IFAM MCP contract. It mirrors the
formats documented by [`xiaolei-lab/IFAM`](https://github.com/xiaolei-lab/IFAM),
but it is **not** the upstream demo data and contains no real human, pig, rice,
or other observations.

Do not use this fixture to estimate accuracy, compare models, or support a
biological claim. It is for schema validation, annotation bookkeeping, and
pipeline plumbing only.

## Contents

| File | Purpose |
| --- | --- |
| `geno/tiny.bed`, `geno/tiny.bim`, `geno/tiny.fam` | PLINK 1 binary genotype set: 12 synthetic individuals, 24 SNPs on chromosomes 1 and 2 |
| `pheno/phenotype.fit.txt` | Fit-ready phenotype file; the four validation IDs are `NA` |
| `pheno/phenotype.truth.txt` | Held-out truth for the independent benchmark runner; the MCP never reads this file |
| `annotations/enhancer.txt` | SNPs `snp01`–`snp08` |
| `annotations/promoter.txt` | SNPs `snp05`–`snp12` |
| `annotations/tfbs.txt` | SNPs `snp09`–`snp16` |
| `annotations/trait_snps.txt` | SNPs `snp18`–`snp21`; designated as a special annotation |
| `splits/repeat-1.json` | Eight training IDs and four validation IDs |
| `expected/inspect_inputs.json` | Expected semantic result of `ifam_inspect_inputs` |
| `fixture.json` | Provenance, counts, upstream pin, and SHA-256 hashes |
| `generate.py` | Deterministic regenerator for every file in this directory |

## Synthetic design

- All 24 SNPs are polymorphic. One genotype (`snp07`, individual `I12`) is
  missing and uses PLINK's missing code `01`.
- The annotation sets intentionally overlap: `enhancer` overlaps `promoter` by
  four SNPs, and `promoter` overlaps `tfbs` by four SNPs. Their union covers 20
  of 24 SNPs (83.33%).
- `trait_snps` is passed as a special annotation stem (`--anno_spec trait_snps`),
  not as a filename. It does not participate in random-effect optimization, but
  it counts toward IFAM's `randomMax`. With the default `randomMax = 5`, the
  effective optimization cap is 4.
- IFAM.R auto-discovers every `*.txt` directly under `annotations/`; it does not
  read an `annotation_names.txt` manifest. Such a manifest is deliberately
  absent because upstream would treat it as an annotation. The current upstream
  script also fails when more than one `--anno_spec` value is supplied, so this
  fixture exercises the supported single-special case.
- `phenotype.fit.txt` masks `I09`–`I12` as `NA`. `phenotype.truth.txt` keeps
  their values but stays outside the MCP boundary. `ifam_fit` must reject a
  split when a validation ID still has a numeric fit phenotype. The independent
  benchmark runner evaluates exported predictions; the MCP itself computes no
  accuracy metric.
- All values are continuous. The binary/AUC path is specified in the contract
  but is not exercised by this fixture.

## Regenerate

```bash
cd agents/ifam/mcp/fixtures/tiny
python3 generate.py
```

The generator uses a fixed seed and rewrites the data files, expected summary,
and `fixture.json` hashes. Review the resulting diff before committing.

## Validation status

Format construction, hash reproducibility, and a byte-level decode are checked
locally; `generate.py` also performs a `.bed` round trip. The file layout was
calibrated on 2026-10-18 against the user-downloaded upstream archive
(SHA-256 `b66f1a6d…91bd2b`, commit `62f8e4cd…f7649`) and `IFAM.R` 1.0.0
(SHA-256 `1ff7efa4…0e0f11`). The fixture has **not** been executed through
`IFAM.R` or HIBLUP v1.1.0, and it has not been checked by PLINK. Those checks
are required before the fixture can support an MCP acceptance case. See
[`../../CONTRACT.md`](../../CONTRACT.md) for the pending verification steps.
