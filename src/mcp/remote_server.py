#!/usr/bin/env python3
"""AgentPay Guard MCP server — remote (Streamable HTTP) transport.

Exposes the AgentPay Guard as a remote MCP server that Claude web/Android can
reach through a public URL (ngrok / Cloudflare Tunnel):

    uvicorn remote_server:app --host 0.0.0.0 --port 8002
    ngrok http 8002
    → add https://<your-subdomain>.ngrok-free.app/mcp in
      Claude → Settings → Connectors → Add custom connector

Implements the MCP Streamable HTTP transport statelessly:
  POST /mcp  with a JSON-RPC message → JSON-RPC response (application/json)
  GET  /mcp  → 405 (no server-initiated streams)
  DELETE /mcp → 200

Env:
  GUARD_API          backend base URL (default http://localhost:8000)
  GUARD_MCP_TOKEN    if set, requests must send `Authorization: Bearer <token>`
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

import guard_tools

app = FastAPI(title="AgentPay Guard MCP (remote)", docs_url=None, redoc_url=None)

MCP_TOKEN = os.environ.get("GUARD_MCP_TOKEN", "")


def _authorized(headers: Any) -> bool:
    if not MCP_TOKEN:
        return True
    auth = headers.get("authorization", "")
    return auth == f"Bearer {MCP_TOKEN}"


def _rpc_result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _rpc_error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle_message(message: dict) -> dict | None:
    method = message.get("method", "")
    msg_id = message.get("id")

    if method == "initialize":
        return _rpc_result(
            msg_id,
            {
                "protocolVersion": guard_tools.PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": guard_tools.SERVER_INFO,
            },
        )
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return _rpc_result(msg_id, {"tools": guard_tools.TOOLS})
    if method == "tools/call":
        params = message.get("params", {})
        try:
            text = guard_tools.dispatch(
                params.get("name", ""),
                params.get("arguments") or params.get("args") or {},
            )
            return _rpc_result(
                msg_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            )
        except guard_tools.GuardUnavailable as exc:
            return _rpc_result(
                msg_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
    if method == "ping":
        return _rpc_result(msg_id, {})
    return _rpc_error(msg_id, -32601, f"Method not found: {method}")


@app.post("/mcp")
async def mcp_post(request: Request) -> Response:
    if not _authorized(request.headers):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    accept = request.headers.get("accept", "")
    try:
        message = await request.json()
    except Exception:
        return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)

    response = handle_message(message)
    if response is None:
        return Response(status_code=202)

    # Streamable HTTP allows a plain application/json response for request/response
    # messaging; Claude's connector accepts this. Advertise SSE capability via Accept
    # echo when the client requested it.
    if "text/event-stream" in accept:
        body = json.dumps(response)
        return Response(
            content=f"event: message\ndata: {body}\n\n",
            media_type="text/event-stream",
        )
    return JSONResponse(response)


@app.get("/mcp")
async def mcp_get() -> Response:
    return JSONResponse(
        {"error": "Server does not offer server-initiated streams (GET /mcp)"},
        status_code=405,
    )


@app.delete("/mcp")
async def mcp_delete() -> Response:
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "server": guard_tools.SERVER_INFO,
        "guard_api": guard_tools.API,
    }


@app.on_event("startup")
async def _startup() -> None:
    guard_tools.register_agent()
