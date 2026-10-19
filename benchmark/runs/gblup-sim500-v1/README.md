# gblup-sim500-v1

Direct baseline control (not the site's MCP record).

- **Status:** exploratory; not certified; not an L1 result.
- **Data:** local 500×5,000 subset of the upstream IFAM demo genotype.
- **Trait:** simulated, h² = 0.5, seed `20261019`; not a paper phenotype.
- **Split:** one 80/20 split; 400 train / 100 validation.
- **Metrics:** Pearson r 0.5075, R² 0.2576, prediction-bias slope 1.2117.
- **Runner:** `agents/ifam/mcp/runner.py` (outside the fitting code).
- **Public record:** `result.json`; site copy at
  `site/data/results/gblup-sim500.json`.
- **Private artifacts:** data and predictions under `local_data/gblup-sim500/`;
  not committed.

This record exists to prove the evidence pipeline end to end. It is not a
reproduction of the IFAM paper or any Duroc result.
