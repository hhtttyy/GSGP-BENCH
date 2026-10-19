#!/usr/bin/env python3
"""Minimal end-to-end acceptance for the IFAM MCP.

The acceptance deliberately separates engineering evidence from scientific
claims:

1. MCP stdio handshake and tools/list.
2. inspect the tiny contract fixture and compare with the golden JSON.
3. If R and HIBLUP are available, build a 500 x 5,000 subset of the upstream
   demo with the independent Python PLINK subsetter, run IFAM.R directly, run
   the same input through the MCP, compare genetic values, export predictions
   and run the independent runner. PLINK itself is optional.

A pass means the wrapper is fit for an exploratory engineering record. It is
not L1 certification, and it never publishes data or credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ifam_core  # noqa: E402


class AcceptanceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MCPClient:
    def __init__(
        self,
        base_root: Path,
        upstream_root: Path | None,
        job_root: Path,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        env = os.environ.copy()
        if upstream_root is not None:
            env["IFAM_ROOT"] = str(upstream_root)
        env["IFAM_MCP_JOB_ROOT"] = str(job_root)
        if extra_env:
            env.update(extra_env)
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(HERE / "server.py"),
                "--base-root",
                str(base_root),
            ],
            cwd=str(HERE),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.next_id = 1
        self.stderr = ""

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        assert self.process.stdin and self.process.stdout
        request_id = self.next_id
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                if self.process.stderr:
                    self.stderr = self.process.stderr.read()
                raise AcceptanceError("MCP_PROCESS_EXIT", f"server exited during {method}: {self.stderr[-1000:]}")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AcceptanceError("MCP_PROTOCOL_ERROR", f"invalid JSON from server: {line[:200]!r}") from exc
            if message.get("id") == request_id:
                if "error" in message:
                    raise AcceptanceError("MCP_ERROR", str(message["error"]))
                return message["result"]

    def notify(self, method: str) -> None:
        assert self.process.stdin
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.process.stdin.flush()

    def initialize(self) -> dict[str, Any]:
        return self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ifam-acceptance", "version": "0.1.0"},
            },
        )

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            payload = result.get("structuredContent") or {"error": result.get("content")}
            raise AcceptanceError("TOOL_ERROR", json.dumps(payload, ensure_ascii=False))
        return result["structuredContent"]

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except OSError:
            pass
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()


def _run(cmd: list[str], log_path: Path, env: dict[str, str] | None = None, timeout: int = 1800) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
        log.write(f"\nexit={process.returncode}\n")
    return process.returncode


def _runtime(upstream_root: Path | None) -> dict[str, Any]:
    old = os.environ.get("IFAM_ROOT")
    if upstream_root is not None:
        os.environ["IFAM_ROOT"] = str(upstream_root)
    try:
        return ifam_core.runtime_status()
    finally:
        if upstream_root is not None:
            if old is None:
                os.environ.pop("IFAM_ROOT", None)
            else:
                os.environ["IFAM_ROOT"] = old


def _extract_demo(upstream_root: Path, work: Path) -> Path:
    demo_zip = upstream_root / "demo_data.zip"
    if not demo_zip.is_file():
        raise AcceptanceError("DEMO_DATA_MISSING", f"{demo_zip} is missing")
    source = work / "demo_source"
    if (source / "demo_data" / "geno" / "demo.bed").is_file():
        return source / "demo_data"
    source.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(demo_zip) as archive:
        wanted = [
            name
            for name in archive.namelist()
            if name.startswith("demo_data/geno/demo.")
            or name == "demo_data/phe/phenotype.txt"
            or (name.startswith("demo_data/annotations/") and name.endswith(".txt"))
        ]
        archive.extractall(source, members=wanted)
    return source / "demo_data"


def _read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _prepare_subset(demo: Path, subset: Path, work: Path, threads: int) -> dict[str, Any]:
    if (subset / "geno" / "demo.bed").is_file() and (work / "subset_manifest.json").is_file():
        return json.loads((work / "subset_manifest.json").read_text(encoding="utf-8"))
    for name in ("geno", "pheno", "annotations", "splits"):
        (subset / name).mkdir(parents=True, exist_ok=True)
    fam_lines = _read_lines(demo / "geno" / "demo.fam")
    fam_rows = [line.split() for line in fam_lines]
    ids = [row[0] for row in fam_rows]
    snp_lines = _read_lines(demo / "geno" / "demo.bim")
    snp_rows = [line.split() for line in snp_lines]
    snp_ids = [row[1] for row in snp_rows]
    annotations = {
        path.stem: _read_lines(path)
        for path in sorted((demo / "annotations").glob("*.txt"))
    }
    universe = sorted(set().union(*(set(values) for values in annotations.values())))
    rng = random.Random(20261018)
    selected_ids = sorted(rng.sample(ids, min(500, len(ids))))
    selected_snps: set[str] = set()
    for values in annotations.values():
        selected_snps.update(rng.sample(values, min(20, len(values))))
    remaining = [snp for snp in universe if snp not in selected_snps]
    rng.shuffle(remaining)
    selected_snps.update(remaining[: max(0, 5000 - len(selected_snps))])
    keep_rows = [row for row in fam_rows if row[0] in set(selected_ids)]
    _python_subset(demo, subset, keep_rows, selected_snps, snp_ids)
    (work / "keep.txt").write_text(
        "\n".join(f"{row[0]} {row[1]}" for row in keep_rows) + "\n", encoding="utf-8"
    )
    (work / "extract.txt").write_text("\n".join(sorted(selected_snps)) + "\n", encoding="utf-8")
    kept_snps = set(line.split()[1] for line in _read_lines(subset / "geno" / "demo.bim"))
    kept_annotations = {}
    for name, values in annotations.items():
        kept = [snp for snp in values if snp in kept_snps]
        if kept:
            (subset / "annotations" / f"{name}.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
            kept_annotations[name] = len(kept)
    if len(kept_annotations) < 2:
        raise AcceptanceError("ANNOTATION_SUBSET_EMPTY", "fewer than two annotations survived subsetting")
    phenotype_lines = _read_lines(demo / "phe" / "phenotype.txt")
    header = phenotype_lines[0]
    phenotype_rows = [line.split("\t") for line in phenotype_lines[1:]]
    pheno_map = {row[0]: row[1] for row in phenotype_rows}
    subset_ids = [line.split()[0] for line in _read_lines(subset / "geno" / "demo.fam")]
    rng_split = random.Random(20261018)
    shuffled = subset_ids[:]
    rng_split.shuffle(shuffled)
    n_val = max(1, round(len(shuffled) * 0.2))
    validation = sorted(shuffled[:n_val])
    validation_set = set(validation)
    training = [sample_id for sample_id in subset_ids if sample_id not in validation_set]
    (subset / "pheno" / "phenotype.fit.txt").write_text(
        header + "\n" + "\n".join(f"{sid}\t{'NA' if sid in validation_set else pheno_map[sid]}" for sid in subset_ids) + "\n",
        encoding="utf-8",
    )
    (subset / "pheno" / "phenotype.truth.txt").write_text(
        header + "\n" + "\n".join(f"{sid}\t{pheno_map[sid]}" for sid in validation) + "\n",
        encoding="utf-8",
    )
    split = {
        "schema_version": "ifam.split.v1",
        "split_id": "demo-500x5k-repeat-1",
        "seed": 20261018,
        "training_ids": training,
        "validation_ids": validation,
    }
    (subset / "splits" / "repeat-1.json").write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "dataset": "upstream-demo-500x5k",
        "n_individuals": len(subset_ids),
        "n_snps": len(kept_snps),
        "annotations": kept_annotations,
        "split": "splits/repeat-1.json",
        "n_validation": len(validation),
        "threads": threads,
        "subset_engine": "independent Python SNP-major subsetter",
        "note": "Derived locally from the upstream demo; not committed and not a publication dataset.",
    }
    (work / "subset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _python_subset(demo: Path, subset: Path, keep_rows: list[list[str]], selected_snps: set[str], snp_ids: list[str]) -> None:
    """Create a SNP-major PLINK subset without calling PLINK."""
    old_fam = [line.split() for line in _read_lines(demo / "geno" / "demo.fam")]
    old_index = {row[0]: index for index, row in enumerate(old_fam)}
    selected_ids = [row[0] for row in keep_rows]
    if any(sample_id not in old_index for sample_id in selected_ids):
        raise AcceptanceError("SUBSET_INVALID", "selected individual is absent from demo .fam")
    old_bim = [line.split() for line in _read_lines(demo / "geno" / "demo.bim")]
    bim_indices = [(index, row) for index, row in enumerate(old_bim) if row[1] in selected_snps]
    if not bim_indices:
        raise AcceptanceError("SUBSET_INVALID", "no selected SNP is present in demo .bim")
    data = (demo / "geno" / "demo.bed").read_bytes()
    old_n = len(old_fam)
    old_width = (old_n + 3) // 4
    if len(data) != 3 + len(old_bim) * old_width or data[:3] != b"\x6c\x1b\x01":
        raise AcceptanceError("SUBSET_INVALID", "demo .bed has an unexpected size or magic")
    new_width = (len(selected_ids) + 3) // 4
    packed = bytearray()
    new_fam: list[str] = []
    new_bim: list[str] = []
    for old_snp_index, row in bim_indices:
        new_fam_row = None
        new_row = bytearray(new_width)
        for new_index, sample_id in enumerate(selected_ids):
            source_index = old_index[sample_id]
            source_byte = data[3 + old_snp_index * old_width + source_index // 4]
            code = (source_byte >> (2 * (source_index % 4))) & 0b11
            new_row[new_index // 4] |= code << (2 * (new_index % 4))
        packed.extend(new_row)
        new_bim.append("\t".join(row))
    new_fam = ["\t".join(row) for row in keep_rows]
    (subset / "geno" / "demo.bed").write_bytes(b"\x6c\x1b\x01" + bytes(packed))
    (subset / "geno" / "demo.bim").write_text("\n".join(new_bim) + "\n", encoding="utf-8")
    (subset / "geno" / "demo.fam").write_text("\n".join(new_fam) + "\n", encoding="utf-8")


def _direct_run(upstream_root: Path, subset: Path, work: Path, threads: int) -> Path:
    rscript = os.environ.get("RSCRIPT") or shutil.which("Rscript")
    hiblup = os.environ.get("HIBLUP") or shutil.which("hiblup")
    if not rscript or not hiblup:
        raise AcceptanceError("RUNTIME_UNAVAILABLE", "Rscript and hiblup must be available")
    ifam_r = upstream_root / "Scripts" / "IFAM.R"
    if ifam_core.sha256_file(ifam_r) != ifam_core.PINNED_IFAM_R_SHA256:
        raise AcceptanceError("UPSTREAM_HASH_MISMATCH", "IFAM.R does not match the pinned hash")
    out = work / "direct_output"
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = str(Path(hiblup).parent) + os.pathsep + env.get("PATH", "")
    cmd = [
        rscript,
        str(ifam_r),
        "--bfile",
        str(subset / "geno" / "demo"),
        "--pheno",
        str(subset / "pheno" / "phenotype.fit.txt"),
        "--anno_folder",
        str(subset / "annotations") + os.sep,
        "--pheno_pos",
        "2",
        "--randomMax",
        "5",
        "--VCmethod",
        "AI",
        "--thread",
        str(threads),
        "--tmp_files",
        "TRUE",
        "--outPath",
        str(out) + os.sep,
        "--output_prefix",
        "IFAM",
    ]
    return_code = _run(cmd, work / "direct_run.log", env=env)
    if return_code != 0:
        raise AcceptanceError("UPSTREAM_FAILED", f"direct upstream run failed; see {work / 'direct_run.log'}")
    rand_path = out / "IFAM_T1.rand"
    if not rand_path.is_file():
        raise AcceptanceError("UPSTREAM_OUTPUT_MISSING", f"direct run did not produce {rand_path.name}")
    return rand_path


def _read_rand(path: Path) -> dict[str, float]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    value_index = header.index("genetic_values")
    values = {}
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) <= value_index:
            continue
        values[fields[0]] = float(fields[value_index])
    return values


def _write_report(work: Path, report: dict[str, Any]) -> None:
    (work / "acceptance_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [f"# IFAM MCP acceptance report", "", f"Status: **{report['status']}**", ""]
    for step in report["steps"]:
        lines.append(f"- **{step['name']}**: {step['status']} — {step.get('detail', '')}")
    lines.extend(["", "This is an engineering/exploratory record, not L1 certification.", ""])
    (work / "acceptance_report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IFAM MCP minimal execution acceptance")
    parser.add_argument("--tiny-root", default=str(HERE / "fixtures" / "tiny"))
    parser.add_argument("--upstream-root", default=os.environ.get("IFAM_ROOT"))
    parser.add_argument("--work-dir", default="/tmp/ifam-acceptance")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--skip-demo", action="store_true")
    args = parser.parse_args(argv)

    work = Path(args.work_dir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    tiny = Path(args.tiny_root).expanduser().resolve()
    upstream = Path(args.upstream_root).expanduser().resolve() if args.upstream_root else None
    steps: list[dict[str, Any]] = []

    def step(name: str, status: str, detail: str = "", **extra: Any) -> None:
        steps.append({"name": name, "status": status, "detail": detail, **extra})

    client = None
    try:
        client = MCPClient(tiny, upstream, work / "jobs")
        init = client.initialize()
        step("mcp_initialize", "pass", f"server={init['serverInfo']['name']} {init['serverInfo']['version']}")
        listed = client.request("tools/list")
        names = [tool["name"] for tool in listed["tools"]]
        expected_tools = ["ifam_inspect_inputs", "ifam_fit", "ifam_job_status", "ifam_export"]
        if names != expected_tools:
            raise AcceptanceError("TOOLS_MISMATCH", f"unexpected tools: {names}")
        step("tools_list", "pass", ", ".join(names))
        actual = client.call(
            "ifam_inspect_inputs",
            {
                "input_root": ".",
                "bfile": "geno/tiny",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "special_annotations": ["trait_snps"],
                "random_max": 5,
                "validation_split": "splits/repeat-1.json",
            },
        )
        expected = json.loads((tiny / "expected" / "inspect_inputs.json").read_text(encoding="utf-8"))
        if actual != expected:
            raise AcceptanceError("INSPECT_GOLDEN_MISMATCH", "inspect output differs from the checked-in golden JSON")
        step("inspect_tiny_golden", "pass", "exact match with fixtures/tiny/expected/inspect_inputs.json")
    except Exception as exc:  # noqa: BLE001
        step("mcp_contract", "fail", f"{type(exc).__name__}: {exc}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "exploratory", "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        if client:
            client.close()
        return 1

    if args.skip_demo:
        step("execution", "skipped", "--skip-demo")
        report = {"schema_version": "ifam.acceptance.v1", "status": "contract_only", "evidence_level": "none", "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 0

    runtime = _runtime(upstream)
    if runtime["blocking_errors"]:
        step(
            "runtime",
            "blocked",
            "; ".join(f"{item['code']}: {item['message']}" for item in runtime["blocking_errors"]),
        )
        report = {"schema_version": "ifam.acceptance.v1", "status": "blocked", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 2
    step("runtime", "pass", "Rscript, HIBLUP and pinned IFAM.R are available; PLINK is optional")

    if upstream is None:
        raise AcceptanceError("UPSTREAM_ROOT_MISSING", "--upstream-root is required for the execution phase")
    demo = _extract_demo(upstream, work)
    step("demo_data", "pass", f"demo source: {demo}")

    subset = work / "demo_500x5k"
    try:
        manifest = _prepare_subset(demo, subset, work, args.threads)
        step("demo_subset", "pass", f"{manifest['n_individuals']} x {manifest['n_snps']} SNPs, {len(manifest['annotations'])} annotations")
    except Exception as exc:  # noqa: BLE001
        step("demo_subset", "fail", f"{type(exc).__name__}: {exc}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 1

    try:
        direct_rand = _direct_run(upstream, subset, work, args.threads)
        step("direct_upstream", "pass", f"direct run produced {direct_rand.name}")
    except Exception as exc:  # noqa: BLE001
        step("direct_upstream", "fail", f"{type(exc).__name__}: {exc}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 1

    try:
        client.close()
        client = MCPClient(subset, upstream, work / "jobs")
        client.initialize()
        fit = client.call(
            "ifam_fit",
            {
                "input_root": ".",
                "bfile": "geno/demo",
                "phenotype": "pheno/phenotype.fit.txt",
                "phenotype_index": 2,
                "annotation_dir": "annotations",
                "random_max": 5,
                "vc_method": "AI",
                "threads": args.threads,
                "validation_split": "splits/repeat-1.json",
                "keep_intermediate": False,
            },
        )
        job_id = fit["job_id"]
        deadline = time.time() + args.timeout
        status = None
        while time.time() < deadline:
            status = client.call("ifam_job_status", {"job_id": job_id})
            if status["state"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(2)
        if status is None or status["state"] != "succeeded":
            raise AcceptanceError("WRAPPER_FIT_FAILED", json.dumps(status, ensure_ascii=False)[:2000])
        step("wrapper_fit", "pass", f"job {job_id} succeeded")
        export = client.call("ifam_export", {"job_id": job_id})
        (work / "export.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
        step(
            "export",
            "pass",
            f"{export['n_predictions']} predictions, {len(export['validation_ids'])} validation IDs",
        )
    except Exception as exc:  # noqa: BLE001
        step("wrapper_fit", "fail", f"{type(exc).__name__}: {exc}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 1

    try:
        direct_values = _read_rand(direct_rand)
        wrapper_values = {item["sample_id"]: item["genetic_value"] for item in export["predictions"]}
        shared = set(direct_values) & set(wrapper_values)
        if not shared:
            raise AcceptanceError("COMPARE_EMPTY", "direct and wrapper predictions have no shared IDs")
        max_diff = max(abs(direct_values[sample_id] - wrapper_values[sample_id]) for sample_id in shared)
        if max_diff > 1e-4:
            raise AcceptanceError("COMPARE_MISMATCH", f"max |direct - wrapper| = {max_diff:.6g}")
        step("prediction_comparison", "pass", f"{len(shared)} shared IDs; max |diff| = {max_diff:.6g}")
    except Exception as exc:  # noqa: BLE001
        step("prediction_comparison", "fail", f"{type(exc).__name__}: {exc}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        client.close()
        return 1
    finally:
        client.close()

    truth = subset / "pheno" / "phenotype.truth.txt"
    fit_phenotype = subset / "pheno" / "phenotype.fit.txt"
    runner_out = work / "evaluation.json"
    cmd = [
        sys.executable,
        str(HERE / "runner.py"),
        "--predictions",
        str(work / "export.json"),
        "--truth",
        str(truth),
        "--fit-phenotype",
        str(fit_phenotype),
        "--split",
        str(subset / "splits" / "repeat-1.json"),
        "--out",
        str(runner_out),
    ]
    return_code = _run(cmd, work / "runner.log")
    if return_code != 0 or not runner_out.is_file():
        step("independent_runner", "fail", f"runner failed; see {work / 'runner.log'}")
        report = {"schema_version": "ifam.acceptance.v1", "status": "failed", "evidence_level": "none", "runtime": runtime, "steps": steps}
        _write_report(work, report)
        print(json.dumps(report, indent=2))
        return 1
    evaluation = json.loads(runner_out.read_text(encoding="utf-8"))
    step(
        "independent_runner",
        "pass",
        f"exploratory n={evaluation['n_validation']} metrics={evaluation['metrics']}",
    )
    step("policy", "pass", "held-out truth stayed outside the MCP; no metric was computed by the server")
    report = {
        "schema_version": "ifam.acceptance.v1",
        "status": "passed",
        "evidence_level": "exploratory",
        "certified": False,
        "runtime": runtime,
        "subset": manifest,
        "prediction_max_abs_diff": max_diff,
        "evaluation": evaluation,
        "steps": steps,
        "note": "Engineering acceptance only. This is not an L1 benchmark record and must not be published as one.",
    }
    _write_report(work, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
