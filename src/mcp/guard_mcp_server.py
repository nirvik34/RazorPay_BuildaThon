#!/usr/bin/env python3
"""AgentPay Guard MCP server — stdio transport (Claude Desktop / Claude Code).

Config in claude_desktop_config.json:
    {"mcpServers": {"agentpay-guard": {"command": "python3",
        "args": ["/abs/path/src/mcp/guard_mcp_server.py"]}}}

For Claude web/Android use remote_server.py instead (Streamable HTTP + tunnel).
"""

from __future__ import annotations

import json
import sys

import guard_tools


def handle(req: dict) -> dict | None:
    method = req.get("method", "")
    msg_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": guard_tools.PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": guard_tools.SERVER_INFO,
            },
        }
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": guard_tools.TOOLS}}
    if method == "tools/call":
        params = req.get("params", {})
        try:
            text = guard_tools.dispatch(
                params.get("name", ""),
                params.get("arguments") or params.get("args") or {},
            )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        except guard_tools.GuardUnavailable as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    guard_tools.register_agent()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
