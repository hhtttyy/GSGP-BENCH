# gblup-sim500-mcp-v1

First real GBLUP evidence record produced through the manual baseline MCP.

- **Status:** exploratory; not certified; not an L1 result.
- **MCP:** gblup 0.1.0, stdio, tools `gblup_inspect_inputs` → `gblup_fit` →
  `gblup_export`.
- **Data:** local 500×5,000 subset of the upstream IFAM demo genotype.
- **Trait:** simulated, h² = 0.5, seed `20261019`; not a paper phenotype.
- **Split:** one 80/20 split; 400 train / 100 validation.
- **Metrics:** Pearson r 0.5075, R² 0.2576, prediction-bias slope 1.2117.
- **Runner:** `agents/ifam/mcp/runner.py` outside the MCP and fitting code.
- **Control:** `gblup-sim500-v1/result.json` (direct script). The MCP result must
  match its scientific metrics within tolerance.
- **Public record:** `result.json`; site copy at
  `site/data/results/gblup-sim500.json`.
- **Private artifacts:** data and predictions under `local_data/gblup-sim500/`;
  not committed.

The MCP is a manual baseline service, not a Paper2Agent-generated MCP. This is
still not a reproduction of the IFAM paper or any Duroc result.
