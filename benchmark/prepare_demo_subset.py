#!/usr/bin/env python3
"""Prepare the local 500x5k genotype subset used by the GBLUP trial.

This reads the already-downloaded upstream IFAM archive and writes only to
local_data/ (gitignored). It never downloads anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "agents" / "ifam" / "mcp"))
from acceptance import _extract_demo, _prepare_subset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the local GBLUP demo subset")
    parser.add_argument("--ifam-root", default=str(Path.home() / "Downloads" / "IFAM-main"))
    parser.add_argument("--work-dir", default=str(REPO / "local_data" / "ifam-demo-prep"))
    parser.add_argument("--out-dir", default=str(REPO / "local_data" / "ifam-demo-500x5k"))
    args = parser.parse_args()
    upstream = Path(args.ifam_root).expanduser().resolve()
    if not (upstream / "demo_data.zip").is_file():
        print(json.dumps({"status": "blocked", "error": f"missing {upstream / 'demo_data.zip'}"}, indent=2))
        return 2
    work = Path(args.work_dir).expanduser().resolve()
    out = Path(args.out_dir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    demo = _extract_demo(upstream, work)
    manifest = _prepare_subset(demo, out, work, threads=1)
    print(json.dumps({"status": "ready", "subset": str(out), "manifest": manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
