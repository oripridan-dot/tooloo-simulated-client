#!/usr/bin/env python3
"""
product_mcp_server.py — TooLoo MCP Bridge Server for TaskFlow
==============================================================
Exposes the product's live context via JSON-RPC 2.0 over HTTP so TooLoo
can read the repository state before writing any code.

Implements the tool contract expected by:
    core/mcp_client/cross_repo_bridge.py  (in tooloo-core)

Supported tools
---------------
    get_project_identity    — project name, stack, config
    get_db_schema           — live SQLite schema
    get_error_logs          — recent stderr / log lines
    get_architecture        — ARCHITECTURE.md contents
    get_source_rules        — source_rules.md contents
    get_directory_structure — recursive directory tree
    get_ast_structure       — class/function map for a file
    get_health_status       — git status + recent commits
    read_file               — read any file in the repo (capped)

Start with:
    python product_mcp_server.py           # port 7000
    python product_mcp_server.py --port 7001
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="TaskFlow MCP Server", version="0.1.0")


# ── Tool dispatch ─────────────────────────────────────────────────────────────

def _text_response(text: str) -> dict:
    """Wrap a string result in the MCP content envelope."""
    return {"content": [{"type": "text", "text": text}]}


def _error_response(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


# ── Tool implementations ──────────────────────────────────────────────────────

def tool_get_project_identity(_args: dict) -> str:
    config_path = ROOT / ".tooloo.config"
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    identity = {
        "project_name": config.get("project_name", "tooloo-simulated-client"),
        "stack": config.get("stack", "Python / FastAPI / SQLite / SQLAlchemy"),
        "description": config.get("description", "Simulated client for TooLoo integration tests"),
        "main_language": "python",
        "framework": "fastapi",
        "database": "sqlite",
        "tooloo_config": config,
    }
    return json.dumps(identity, indent=2)


def tool_get_db_schema(_args: dict) -> str:
    db_path = ROOT / "data" / "taskflow.db"
    if not db_path.exists():
        return "(Database not initialised — run the API server first)"
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "(No tables found)"
        return "\n\n".join(r[0] for r in rows if r[0])
    except Exception as exc:
        return f"(DB schema error: {exc})"


def tool_get_error_logs(args: dict) -> str:
    lines = int(args.get("lines", 100))
    log_path = ROOT / "data" / "error.log"
    if not log_path.exists():
        return "(No error log found — error.log not yet created)"
    try:
        with open(log_path) as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except Exception as exc:
        return f"(Log read error: {exc})"


def tool_get_architecture(_args: dict) -> str:
    arch_path = ROOT / "ARCHITECTURE.md"
    if not arch_path.exists():
        return "(ARCHITECTURE.md not found)"
    return arch_path.read_text()


def tool_get_source_rules(_args: dict) -> str:
    rules_path = ROOT / "source_rules.md"
    if not rules_path.exists():
        return "(source_rules.md not found)"
    return rules_path.read_text()


def tool_get_directory_structure(args: dict) -> int | str:
    depth = int(args.get("depth", 3))
    try:
        result = subprocess.run(
            ["find", str(ROOT), "-maxdepth", str(depth),
             "!", "-path", "*/.git/*",
             "!", "-path", "*/__pycache__/*",
             "!", "-path", "*/data/taskflow.db",
             "-print"],
            capture_output=True, text=True, timeout=10,
        )
        lines = sorted(result.stdout.strip().splitlines())
        # Convert absolute paths to relative
        rel_lines = [line.replace(str(ROOT) + "/", "") for line in lines]
        return "\n".join(rel_lines)
    except Exception as exc:
        return f"(directory structure error: {exc})"


def tool_get_ast_structure(args: dict) -> str:
    file_path = args.get("file_path", "")
    if not file_path:
        return "(file_path argument required)"

    target = ROOT / file_path
    if not target.exists():
        return f"(File not found: {file_path})"
    if not target.suffix == ".py":
        return f"(Only .py files supported, got: {file_path})"

    try:
        source = target.read_text()
        tree = ast.parse(source, filename=str(target))
    except SyntaxError as exc:
        return f"(SyntaxError in {file_path}: {exc})"

    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbols.append(f"  [{kind}] {node.name}  (line {node.lineno})")

    return f"# AST map: {file_path}\n" + ("\n".join(symbols) or "  (no symbols found)")


def tool_get_health_status(_args: dict) -> str:
    parts: list[str] = []

    try:
        git_status = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--short"],
            capture_output=True, text=True, timeout=5,
        )
        parts.append("## Git Status\n" + (git_status.stdout.strip() or "(clean)"))
    except Exception as exc:
        parts.append(f"## Git Status\n(error: {exc})")

    try:
        git_log = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--oneline", "-10"],
            capture_output=True, text=True, timeout=5,
        )
        parts.append("## Recent Commits\n" + (git_log.stdout.strip() or "(no commits)"))
    except Exception as exc:
        parts.append(f"## Recent Commits\n(error: {exc})")

    parts.append(f"## Server\nproduct_mcp_server.py running — root: {ROOT}")
    return "\n\n".join(parts)


def tool_read_file(args: dict) -> str:
    file_path = args.get("file_path", "")
    max_chars = int(args.get("max_chars", 8000))
    if not file_path:
        return "(file_path argument required)"

    target = ROOT / file_path
    # Prevent path traversal outside root
    try:
        target.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return "(Access denied: path outside repo root)"

    if not target.exists():
        return f"(File not found: {file_path})"
    try:
        content = target.read_text(errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... (truncated at {max_chars} chars)"
        return content
    except Exception as exc:
        return f"(Read error: {exc})"


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS: dict = {
    "get_project_identity": tool_get_project_identity,
    "get_db_schema": tool_get_db_schema,
    "get_error_logs": tool_get_error_logs,
    "get_architecture": tool_get_architecture,
    "get_source_rules": tool_get_source_rules,
    "get_directory_structure": tool_get_directory_structure,
    "get_ast_structure": tool_get_ast_structure,
    "get_health_status": tool_get_health_status,
    "read_file": tool_read_file,
}


# ── MCP JSON-RPC endpoint ─────────────────────────────────────────────────────

@app.post("/mcp")
async def mcp_dispatch(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_error_response(None, -32700, "Parse error"), status_code=400)

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    if method != "tools/call":
        return JSONResponse(
            _error_response(req_id, -32601, f"Method not found: {method}"),
            status_code=404,
        )

    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    handler = TOOLS.get(tool_name)
    if handler is None:
        return JSONResponse(
            _error_response(req_id, -32602, f"Unknown tool: {tool_name}"),
            status_code=404,
        )

    try:
        result_text = handler(arguments)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": _text_response(str(result_text)),
        })
    except Exception as exc:
        return JSONResponse(
            _error_response(req_id, -32603, f"Internal error: {exc}"),
            status_code=500,
        )


@app.get("/mcp/tools")
async def list_tools():
    """Returns the list of available tools (for discovery)."""
    return {
        "tools": [
            {"name": k, "description": v.__doc__ or ""}
            for k, v in TOOLS.items()
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "taskflow-mcp-server"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TaskFlow MCP Server")
    parser.add_argument("--port", type=int, default=7000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(f"[MCP] TaskFlow MCP server starting on http://{args.host}:{args.port}")
    print(f"[MCP] Root: {ROOT}")
    print(f"[MCP] Tools: {', '.join(TOOLS.keys())}")
    uvicorn.run("product_mcp_server:app", host=args.host, port=args.port, reload=False)
