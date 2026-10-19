#!/usr/bin/env python3
"""Minimal IFAM MCP server over stdio.

The server deliberately uses only the Python standard library for the MCP
transport. A real MCP client can initialize this process, list tools, and call
the four tools defined in tools.json. Fit jobs run on the local worker and are
polled with ifam_job_status.

Environment:
  IFAM_MCP_INPUT_ROOT  Root for all relative input paths (default: cwd)
  IFAM_MCP_JOB_ROOT    Directory for job state (default: /tmp/ifam-mcp-jobs)
  IFAM_ROOT            Extracted upstream IFAM checkout, used by fit
  RSCRIPT              Path to Rscript (default: PATH lookup)
  HIBLUP               Path to hiblup (default: PATH lookup)
  HIBLUP_VERSION       Version string stored in provenance (default: 1.1.0)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from ifam_core import (
    IfamError,
    export_job,
    get_job_status,
    inspect_dataset,
    runtime_status,
    submit_fit,
)

HERE = Path(__file__).resolve().parent
TOOLS_PATH = HERE / "tools.json"
SERVER_NAME = "ifam"
SERVER_VERSION = "0.1.0"


def _load_contract() -> dict[str, Any]:
    return json.loads(TOOLS_PATH.read_text(encoding="utf-8"))


def _tool_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {tool["name"]: tool for tool in contract["tools"]}


def _validate_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Validate with jsonschema when available, with a small fallback otherwise."""

    try:
        import jsonschema

        jsonschema.validate(arguments, tool["inputSchema"])
        return
    except ImportError:
        pass
    except Exception as exc:  # jsonschema.ValidationError and other validation errors
        raise IfamError("VALIDATION_ERROR", str(exc)) from exc

    schema = tool["inputSchema"]
    required = schema.get("required", [])
    for key in required:
        if key not in arguments:
            raise IfamError("VALIDATION_ERROR", f"missing required argument {key}")
    if schema.get("additionalProperties") is False:
        extra = set(arguments) - set(schema.get("properties", {}))
        if extra:
            raise IfamError("VALIDATION_ERROR", f"unknown arguments: {sorted(extra)}")


def _call_tool(name: str, arguments: dict[str, Any], base_root: Path) -> Any:
    contract = _load_contract()
    tools = _tool_map(contract)
    if name not in tools:
        raise IfamError("TOOL_NOT_FOUND", f"unknown tool {name}")
    _validate_arguments(tools[name], arguments)
    if name == "ifam_inspect_inputs":
        result, _ = inspect_dataset(base_root=base_root, **arguments)
        return result
    if name == "ifam_fit":
        return submit_fit(base_root=base_root, **arguments)
    if name == "ifam_job_status":
        return get_job_status(arguments["job_id"])
    if name == "ifam_export":
        return export_job(arguments["job_id"])
    raise IfamError("TOOL_NOT_FOUND", f"unknown tool {name}")


def _write(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _tool_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
        "structuredContent": payload,
        "isError": False,
    }


def _tool_error(exc: IfamError) -> dict[str, Any]:
    payload = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
            "details": exc.details,
        }
    }
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
        "structuredContent": payload,
        "isError": True,
    }


def _handle(request: dict[str, Any], base_root: Path) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested if isinstance(requested, str) and requested else "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method in {"notifications/initialized", "initialized", "notifications/cancelled"}:
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        contract = _load_contract()
        listed = []
        for tool in contract["tools"]:
            item = {
                "name": tool["name"],
                "title": tool.get("title", tool["name"]),
                "description": tool.get("description", ""),
                "inputSchema": tool["inputSchema"],
            }
            if "outputSchema" in tool:
                item["outputSchema"] = tool["outputSchema"]
            if "annotations" in tool:
                item["annotations"] = tool["annotations"]
            listed.append(item)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": listed}}
    if method == "tools/call":
        if not isinstance(params, dict):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "params must be an object"},
            }
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "tools/call requires name and an object arguments"},
            }
        try:
            result = _call_tool(name, arguments, base_root)
            return {"jsonrpc": "2.0", "id": request_id, "result": _tool_result(result)}
        except IfamError as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": _tool_error(exc)}
        except Exception as exc:  # pragma: no cover - defensive boundary
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": _tool_error(
                    IfamError("INTERNAL_ERROR", f"{type(exc).__name__}: {exc}", retryable=False)
                ),
            }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IFAM MCP stdio server")
    parser.add_argument("--base-root", default=os.environ.get("IFAM_MCP_INPUT_ROOT", "."))
    parser.add_argument("--job-root", default=None, help="sets IFAM_MCP_JOB_ROOT")
    parser.add_argument("--upstream-root", default=None, help="sets IFAM_ROOT")
    parser.add_argument("--runtime-status", action="store_true", help="print runtime availability and exit")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)

    if args.job_root:
        os.environ["IFAM_MCP_JOB_ROOT"] = args.job_root
    if args.upstream_root:
        os.environ["IFAM_ROOT"] = args.upstream_root
    base_root = Path(args.base_root).expanduser().resolve()
    if args.version:
        print(f"{SERVER_NAME} {SERVER_VERSION}")
        return 0
    if args.runtime_status:
        print(json.dumps(runtime_status(), indent=2))
        return 0
    if not base_root.is_dir():
        print(f"base root is not a directory: {base_root}", file=sys.stderr)
        return 2

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _write({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})
            continue
        if isinstance(request, list):
            responses = []
            for item in request:
                if isinstance(item, dict):
                    response = _handle(item, base_root)
                    if response is not None:
                        responses.append(response)
            if responses:
                _write(responses)
            continue
        if not isinstance(request, dict):
            _write({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            continue
        response = _handle(request, base_root)
        if response is not None:
            _write(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
