# GBLUP baseline MCP

Manual baseline MCP over stdio. It wraps the same GBLUP/REML code as the
evidence trial and is **not** a Paper2Agent-generated or certified service.

## Run

```bash
export GBLUP_MCP_RUN_ROOT=/tmp/gblup-mcp-runs
python3 benchmark/algorithms/gblup/server.py \
  --base-root "$PWD/local_data/gblup-sim500"
```

Tools:

- `gblup_inspect_inputs`
- `gblup_fit`
- `gblup_export`

`gblup_fit` requires `validation_split`; validation IDs must be `NA` in the fit
phenotype. It never reads truth and never computes metrics.

## End-to-end trial

```bash
python3 benchmark/run_gblup_mcp_trial.py \
  --run-id gblup-sim500-mcp-v1
```

This writes:

- `benchmark/runs/gblup-sim500-mcp-v1/result.json`
- `benchmark/runs/gblup-sim500-mcp-v1/metrics.json`
- `site/data/results/gblup-sim500.json`
- `benchmark/datasets/sim500.json`

The direct baseline record `benchmark/runs/gblup-sim500-v1/result.json` is kept
as a control; the MCP result must match its scientific metrics within tolerance.

## Boundary

- Manual baseline, not Paper2Agent-generated.
- Not certified; results are **EXP**.
- Static site cannot execute this MCP; it is a local/worker service.
