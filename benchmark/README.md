# GSGP-Bench evidence layer

This directory turns a prediction run into an auditable result record. It is
method-agnostic and does not depend on HIBLUP or the IFAM MCP.

## Current real run

`benchmark/runs/gblup-sim500-mcp-v1/result.json` is the first non-stub result
produced through a real MCP:

- algorithm: GBLUP (VanRaden GRM, single random effect REML), manual baseline MCP
- data: 500 individuals × 5,000 SNPs, derived locally from the public upstream
  IFAM demo genotype
- trait: simulated, h² = 0.5, seed `20261019`
- split: one 80/20 split, 400 training / 100 validation
- metrics: Pearson r = 0.5075, R² = 0.2576, bias slope = 1.2117
- evidence: `exploratory`, single split, not certified

The direct baseline record `benchmark/runs/gblup-sim500-v1/result.json` is kept
as a control. The MCP result must match its scientific metrics within tolerance.
The site reads the MCP record from `site/data/results/gblup-sim500.json` and
renders it as **EXP**, distinct from L1 and L3.

## Layout

```text
benchmark/
  schema/result.v1.json          result record contract
  algorithms/gblup/              manual baseline SKILL + MCP + certification
  datasets/sim500.json           dataset manifest (source, simulation, hashes)
  run_gblup_sim.py               direct baseline trial (control)
  run_gblup_mcp_trial.py         GBLUP MCP → export → runner → evidence trial
  run_ifam_stub_sim.py           IFAM.R + fake HIBLUP STUB → runner → evidence
  runs/<run_id>/result.json      public, aggregate-only evidence record
  runs/<run_id>/metrics.json     independent runner output
local_data/                      gitignored: genotype, phenotype, predictions
site/data/results/               public site-facing copies of result records
```

Raw genotype, phenotype and individual predictions are **not committed**. The
public record contains aggregate metrics, split metadata, hashes and provenance.

## Reproduce

If `local_data/ifam-demo-500x5k` is absent:

```bash
python3 benchmark/prepare_demo_subset.py \
  --ifam-root "$HOME/Downloads/IFAM-main"
```

Then run the direct baseline (control):

```bash
python3 benchmark/run_gblup_sim.py \
  --source-subset local_data/ifam-demo-500x5k \
  --run-id gblup-sim500-v1
```

Then run the same baseline through its local MCP and write the site record:

```bash
python3 benchmark/run_gblup_mcp_trial.py \
  --run-id gblup-sim500-mcp-v1
```

`local_data/ifam-demo-500x5k` is a local 500×5,000 subset of the upstream IFAM
demo. The result is deterministic for the given seed and input. The run script:

1. copies the local genotype subset;
2. simulates a trait with a known h²;
3. writes a fit phenotype (validation IDs = `NA`) and held-out truth;
4. fits GBLUP with REML and predicts the validation IDs;
5. sends predictions, truth, split and fit phenotype to
   `agents/ifam/mcp/runner.py`;
6. writes the public result JSON and a private predictions file.

The MCP version uses `gblup_inspect_inputs` → `gblup_fit` → `gblup_export` over
stdio. The MCP never reads truth and never computes metrics. It is a manual
baseline MCP, not a Paper2Agent-generated MCP. It has a certification record in `algorithms/gblup/certification.json`:
the package is **certified** by central testing; it is not hosted online and the
result remains EXP.

## IFAM STUB lane

`benchmark/runs/ifam-stub-sim500-v1/result.json` fills the IFAM × sim500 cell:

- real IFAM.R 1.0.0 orchestration through the local IFAM MCP;
- fake HIBLUP engine (`agents/ifam/mcp/stub_runtime/hiblup`);
- independently scored but **scientifically meaningless**;
- evidence level `stub`, site status `STUB`.

Use it only to demonstrate the Paper2Agent/MCP → runner → evidence pipeline.

The fitting code never reads the truth file. Only the independent runner does.

## Evidence levels

- `exploratory`: one split, real computation, no certification. This GBLUP run.
- `l1`: multi-repeat protocol, reviewed, comparable.
- `l2`: different input modality/protocol, explicitly not paper-exact.
- `l3`: paper-reported reference, not reproduced locally.

A single split must never be promoted to L1 merely because the code is real.
The current GBLUP run is deliberately **EXP**.

See [`docs/证据等级与记录.md`](../docs/证据等级与记录.md) for the full status
vocabulary and [`docs/端到端示例-GBLUP.md`](../docs/端到端示例-GBLUP.md) for the
walkthrough from paper/data source to the site.
