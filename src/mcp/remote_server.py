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
from starlette.concurrency import run_in_threadpool

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
            # MCP spec field is "arguments"; accept "args" for backwards compat.
            # NOTE: dispatched via run_in_threadpool at the call site — purchase
            # can block for minutes waiting for the user's phone decision.
            args = params.get("arguments") or params.get("args") or {}
            text = guard_tools.dispatch(params.get("name", ""), args)
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

    # tools/call can block for minutes (waiting for the user's phone decision),
    # so run the handler in a worker thread and keep the event loop responsive.
    response = await run_in_threadpool(handle_message, message)
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


CHECKOUT_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentPay Guard — Secure Checkout</title>
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #F7F9FC;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border: 1px solid #E4E7EC; border-radius: 14px; padding: 32px;
           width: 340px; text-align: center; box-shadow: 0 12px 32px rgba(16,24,40,.12); }}
  .badge {{ background: #EFF8FF; color: #175CD3; font-size: 11px; font-weight: 700;
            padding: 4px 10px; border-radius: 999px; letter-spacing: .5px; }}
  h1 {{ font-size: 18px; margin: 14px 0 4px; }}
  .amount {{ font-size: 32px; font-weight: 800; margin: 10px 0; }}
  .meta {{ color: #667085; font-size: 13px; }}
  .status {{ margin-top: 18px; font-size: 14px; font-weight: 600; min-height: 20px; }}
  .ok {{ color: #067647 }} .bad {{ color: #B42318 }}
  button {{ margin-top: 16px; width: 100%; padding: 13px; border: 0; border-radius: 8px;
            background: #2563EB; color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; }}
</style>
</head>
<body>
<div class="card">
  <span class="badge">AGENTPAY GUARD · USER APPROVED</span>
  <h1>{product}</h1>
  <div class="meta">merchant: {merchant} · order {order_id}</div>
  <div class="amount">₹{rupees}</div>
  <div class="meta">Complete payment to execute the authorized purchase.<br>Single-use authorization · expires in 5 min.</div>
  <div class="status" id="status">Opening Razorpay…</div>
  <button onclick="pay()">PAY NOW</button>
</div>
<script>
var ORDER = "{order_id}";
var AUTH  = "{auth_id}";
function pay() {{
  document.getElementById('status').textContent = '';
  var rzp = new Razorpay({{
    key: "{key_id}",
    order_id: ORDER,
    name: "AgentPay Guard",
    description: "{product}",
    theme: {{ color: "#2563EB" }},
    prefill: {{ name: "AgentPay User" }},
    handler: function (r) {{
      document.getElementById('status').textContent = 'Verifying payment…';
      fetch('/checkout/confirm', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          payment_id: r.razorpay_payment_id,
          order_id: r.razorpay_order_id,
          authorization_id: AUTH
        }})
      }})
      .then(function (res) {{ return res.json(); }})
      .then(function (out) {{
        var s = document.getElementById('status');
        if (out.ok && out.payment.status === 'captured') {{
          s.className = 'status ok';
          s.textContent = '✅ Payment captured — ' + out.payment.id;
        }} else {{
          s.className = 'status bad';
          s.textContent = 'Status: ' + (out.payment ? out.payment.status : 'unknown');
        }}
      }})
      .catch(function () {{
        document.getElementById('status').className = 'status bad';
        document.getElementById('status').textContent = 'Verification failed — check AgentPay audit.';
      }});
    }},
    modal: {{ ondismiss: function () {{
      document.getElementById('status').className = 'status bad';
      document.getElementById('status').textContent = 'Checkout closed — payment not completed.';
    }}}}
  }});
  rzp.open();
}}
window.onload = pay;
</script>
</body>
</html>"""


@app.get("/checkout/{authorization_id}")
def checkout_page(authorization_id: str) -> Response:
    try:
        info = guard_tools.http("GET", f"/guard/payments/order/{authorization_id}")
    except Exception:
        return Response(
            "Authorization not found or expired.",
            status_code=404,
            media_type="text/plain",
        )
    if not info.get("live"):
        return Response(
            "This purchase runs in simulated mode (no Razorpay keys configured) — payment auto-captured.",
            media_type="text/plain",
        )
    if info.get("status") == "captured":
        return Response(
            "✅ This payment was already completed and captured.",
            media_type="text/plain",
        )
    html = CHECKOUT_PAGE.format(
        product=info["product"],
        merchant=info["merchant"],
        order_id=info["orderId"],
        key_id=info["keyId"],
        auth_id=authorization_id,
        rupees=info["amount"] // 100,
    )
    return Response(content=html, media_type="text/html")


@app.post("/checkout/confirm")
def checkout_confirm(payload: dict) -> dict:
    return guard_tools.http(
        "POST",
        "/guard/payments/razorpay/callback",
        {
            "payment_id": payload.get("payment_id"),
            "order_id": payload.get("order_id"),
            "authorization_id": payload.get("authorization_id"),
        },
        timeout=60,
    )


@app.on_event("startup")
async def _startup() -> None:
    guard_tools.register_agent()
