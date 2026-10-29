# SBayesRC MCP server — usage

An MCP server exposing six SBayesRC analysis tools. The server is Python
(FastMCP 4.0.3) but runs **all** scientific computation in the original
SBayesRC R package via `Rscript` — no method logic is reimplemented in Python.

## Tools

| MCP tool | Upstream R function | Purpose |
|----------|--------------------|---------|
| `sbayesrc_tidy_summary` | `SBayesRC::tidy` | QC a GWAS summary file against an LD reference (allele/frequency/N checks) |
| `sbayesrc_impute_summary` | `SBayesRC::impute` | Impute missing summary statistics from the LD reference |
| `sbayesrc_sbayesrc_run` | `SBayesRC::sbayesrc` | Run the SBayesRC Bayesian mixture model (SNP weights, heritability, annotation enrichment) |
| `sbayesrc_prs` | `SBayesRC::prs` | Compute polygenic scores from weights + PLINK genotypes (via `plink2`) |
| `sbayesrc_sbrc_multi` | `SBayesRC::sbrcMulti` | Combine two ancestry-specific PRSs with a tuning sample |
| `sbayesrc_cut_ld` | `SBayesRC::cutLD` | Reduce an LD reference to a different eigen variance threshold |

## Package layout

```
sbayesrc-mcp/
├── USAGE.md                 this file
├── src/
│   ├── sbayesrc_mcp.py      server entry point (mounts the tools)
│   ├── tools/sbayesrc.py    FastMCP tools (JSON contract, Rscript subprocess)
│   ├── r_scripts/sbayesrc.R R dispatcher that calls the SBayesRC functions
│   └── requirements.txt     pinned Python runtime dependencies
└── renv.lock                pinned R library snapshot (restore target)
```

> **This package does not vendor the SBayesRC R source** (it is GPL-3.0). Obtain it
> from the pinned upstream commit / release tarball listed in `UPSTREAM.md` and
> install it into the renv library (see *Restoring the R library* below).

## Prerequisites

- **Python 3.12** — create a venv and `pip install -r src/requirements.txt`
  (FastMCP 4.0.3, mcp).
- **R 4.4.3** — with the SBayesRC package installed. Restore the library from
  `renv.lock` (see *Restoring the R library*). The tested toolchain was
  R 4.4.3 with a gcc/GCC-13+ build; **BH must be pinned to 1.84.0** (the package
  builds with `CXX_STD=CXX11`, which newer BH releases break).
- **plink2** — a static binary is required by the `prs` tool; make it available
  on `PATH` or point `P2A_PLINK2` at it.

## Configuration

The server reads runtime paths from **environment variables in its MCP stdio
launch configuration** (not from the client process). All are optional; each
falls back to a default relative to the installed package.

| Variable | Meaning | Default |
|----------|---------|---------|
| `P2A_RSCRIPT` | Path to `Rscript` | `Rscript` on `PATH` |
| `P2A_R_PROJECT` | renv project directory to load | `<package>/r-runtime` |
| `P2A_PLINK2` | Path to the `plink2` binary | `plink2` on `PATH` |

Example MCP client config (stdio) — replace `</path/to/sbayesrc-mcp>` with the
extracted package location and `</path/to/python>` with the venv interpreter:

```json
{
  "mcpServers": {
    "sbayesrc": {
      "command": "</path/to/python>",
      "args": ["</path/to/sbayesrc-mcp>/src/sbayesrc_mcp.py"],
      "env": {
        "P2A_RSCRIPT": "Rscript",
        "P2A_R_PROJECT": "</path/to/sbayesrc-mcp>/r-runtime",
        "P2A_PLINK2": "plink2"
      }
    }
  }
}
```

## Installation

```bash
# 1) Python environment
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r src/requirements.txt

# 2) R library: create an renv project, restore renv.lock, install SBayesRC from
#    the pinned upstream source (NOT bundled) -- see below
# 3) plink2 on PATH, then start the server via your MCP client per the config above
```

### Restoring the R library

Create an renv project directory (this package uses `r-runtime/` as the default
`P2A_R_PROJECT`, but any path works). `renv.lock` pins every package version the
tools were tested against. From an R session with `renv` available:

```r
# choose a project dir; r-runtime/ matches the default P2A_R_PROJECT
renv::restore(lockfile = "renv.lock", library = "r-runtime/renv/library")
```

The SBayesRC package itself is not on CRAN. This package does **not** bundle it
(GPL-3.0). Install it from the pinned upstream commit / release tarball listed in
`UPSTREAM.md`, e.g.:

```r
install.packages(
  "https://github.com/zhilizheng/SBayesRC/releases/download/v0.2.6/SBayesRC_0.2.6.tar.gz",
  repos = NULL, type = "source")
```

Point `P2A_R_PROJECT` at the renv project directory so the dispatcher loads the
restored library. If the exact lockfile versions are unavailable on your
platform, install equivalent versions of `data.table`, `Matrix`, `Rcpp`,
`RcppEigen` and the SBayesRC source, and set `P2A_R_PROJECT` to that library.

## Typical workflow

```
sbayesrc_tidy_summary   (mafile, ld_dir, output)            -> tidied summary
sbayesrc_impute_summary (mafile=tidied, ld_dir, output)     -> imputed .ma
sbayesrc_sbayesrc_run   (mafile=imputed, ld_dir, out_prefix[, annot, MCMC knobs])
                        -> <out_prefix>.txt weights, .par estimates, enrichment files
sbayesrc_prs            (weight=<out_prefix>.txt, geno_prefix=<plink bfile>, out_prefix)
                        -> <out_prefix>.score.txt
sbayesrc_sbrc_multi     (prs1, prs2, out_prefix, tuneid, pheno)  # cross-ancestry only
sbayesrc_cut_ld         (input_ld, output_ld, thresh)            # optional LD reduction
```

Every tool writes its artifacts to the paths you pass and returns a JSON object
with `status`, `tool`, `outputs`, `summary`, `message` and `reference` keys.
Diagnostics that upstream would print are suppressed (`log2file=FALSE`) so the
MCP stdout stays a clean JSON contract. Output directories are created when the
tools run.

## Known limitations

- **`sbayesrc_run` is not bit-reproducible.** The pinned upstream C++
  (`src/dist.cpp`) draws from an unseeded `thread_local std::mt19937_64`; the
  `seed` parameter is accepted but does not seed that RNG. Runs on identical
  input give hsq ≈ 2.2–2.9. Reproducible structural properties (SNP set/order,
  artifact schema, PIP range) are stable; exact numeric equality is not.
- **Custom LD generation is not exposed.** `LDstep1/2` require the external
  `gctb` binary, which is not bundled.
- **Reference resources** (baseline LD matrices, ~7M-SNP annotation files) are
  multi-GB files hosted off-repo and are not included; supply your own paths.
- `cutLD` at a genuinely lower threshold produces no visible reduction on tiny
  toy LD (blocks are already truncated at 0.995).
- **Platforms:** tested on Linux x86-64 only. Bundling/citing a native `plink2`
  does not make the package portable to other platforms.

## Validation scope

Validated on the bundled deterministic toy dataset (60 samples × 18 SNPs,
3 LD blocks): 27 automated tests driving the server over stdio against an
independent direct-R reference; strict real-call validation in two interpreters
(6/6 tools, 8 acceptance cases each); independent scientific verification that
the tools call the SBayesRC R functions faithfully and reproduce the direct-R
reference for the deterministic tools. This covers the six selected tools only;
it does not establish whole-repository or whole-paper reproduction.
</content>
