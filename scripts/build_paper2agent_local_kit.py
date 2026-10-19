#!/usr/bin/env python3
"""Build the downloadable Paper2Agent local generation kit for the static site.

The kit contains the existing skills/paper2agent tree plus a short local-kit
README, prompt, submission template and the repository license. It does not
contain paper data, code checkouts or generated MCPs.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "paper2agent"
OUT = ROOT / "site" / "resources" / "generate"
ZIP_PATH = OUT / "paper2agent-local-kit.zip"
MANIFEST_PATH = OUT / "kit-manifest.json"
ZIP_DATE = (2026, 10, 19, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_include(path: Path) -> bool:
    return (
        path.is_file()
        and "__pycache__" not in path.parts
        and path.name not in {".DS_Store"}
        and not path.name.endswith(".pyc")
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_files = sorted(path for path in SOURCE.rglob("*") if should_include(path))
    extras = [
        (ROOT / "docs" / "Paper2Agent-Local-Kit.md", "LOCAL_KIT_README.md"),
        (ROOT / "docs" / "Paper2Agent-Prompt.md", "PROMPT.md"),
        (ROOT / ".github" / "ISSUE_TEMPLATE" / "mcp-submission.yml", "mcp-submission.yml"),
        (ROOT / "LICENSE", "LICENSE"),
    ]
    entries: list[dict] = []
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in source_files:
            relative = path.relative_to(SOURCE).as_posix()
            arcname = f"paper2agent/{relative}"
            archive.write(path, arcname)
            entries.append({"path": arcname, "bytes": path.stat().st_size, "sha256": sha256(path)})
        for source, name in extras:
            if not source.is_file():
                raise FileNotFoundError(source)
            arcname = f"paper2agent/{name}"
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
            entries.append({"path": arcname, "bytes": source.stat().st_size, "sha256": sha256(source)})
    manifest = {
        "schema_version": "paper2agent.local-kit.v1",
        "name": "paper2agent-local-kit",
        "source": "skills/paper2agent",
        "license": "MIT (repository LICENSE)",
        "generated_on": "2026-10-19",
        "file_count": len(entries),
        "zip_bytes": ZIP_PATH.stat().st_size,
        "zip_sha256": sha256(ZIP_PATH),
        "top_level_directory": "paper2agent",
        "includes": ["Paper2Agent skills", "local kit README", "prompt", "MCP submission template", "MIT license"],
        "not_included": ["papers", "code checkouts", "datasets", "generated MCP packages", "credentials"],
        "files": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built {ZIP_PATH.relative_to(ROOT)} ({len(entries)} files, {ZIP_PATH.stat().st_size} bytes)")
    print(f"SHA-256: {manifest['zip_sha256']}")


if __name__ == "__main__":
    main()
