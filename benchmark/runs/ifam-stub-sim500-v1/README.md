# ifam-stub-sim500-v1

IFAM × GSGP-Sim 500×5k **STUB** record for the Paper2Agent/MCP lane.

- Real `IFAM.R` 1.0.0 is orchestrated through the local IFAM MCP over stdio.
- The HIBLUP engine is **fake** (`agents/ifam/mcp/stub_runtime/hiblup`), so the
  predictions and metrics have no scientific meaning.
- The independent runner computed the metrics from held-out truth, but the
  values are deliberately not interpreted.
- The site shows this cell as **STUB**, not IFAM reproduction or L1.
- Public record: `result.json`; site copy:
  `site/data/results/ifam-stub-sim500.json`.

This record exists only to demonstrate the Paper2Agent/MCP → runner → evidence
pipeline while HIBLUP v1.1.0 is unavailable.
