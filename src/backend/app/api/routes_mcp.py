"""MCP Streamable-HTTP transport mounted directly on the Guard backend.

Lets a single public URL (ngrok → :8000) serve both the REST API and the MCP
endpoint for Claude connectors, plus the Razorpay checkout pages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

MCP_DIR = Path(__file__).resolve().parent.parent.parent.parent / "mcp"
sys.path.insert(0, str(MCP_DIR))

import guard_tools  # noqa: E402

router = APIRouter(tags=["mcp"])


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
            args = params.get("arguments") or params.get("args") or {}
            # Threadpool offload happens at the call site (async route).
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


@router.post("/mcp")
async def mcp_post(request: Request) -> Response:
    accept = request.headers.get("accept", "")
    try:
        message = await request.json()
    except Exception:
        return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)

    # tools/call can block for minutes awaiting the phone decision → threadpool.
    # Checkout links must point at THIS origin (e.g. the ngrok URL Claude uses),
    # so derive PUBLIC_URL from the incoming request instead of an env default.
    guard_tools.PUBLIC_URL = str(request.base_url).rstrip("/")
    response = await run_in_threadpool(handle_message, message)
    if response is None:
        return Response(status_code=202)
    if "text/event-stream" in accept:
        body = json.dumps(response)
        return Response(
            content=f"event: message\ndata: {body}\n\n", media_type="text/event-stream"
        )
    return JSONResponse(response)


@router.get("/mcp")
async def mcp_get() -> Response:
    return JSONResponse(
        {"error": "Server does not offer server-initiated streams (GET /mcp)"},
        status_code=405,
    )


@router.delete("/mcp")
async def mcp_delete() -> Response:
    return Response(status_code=200)


CHECKOUT_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentPay Guard — Secure Checkout</title>
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #F7F9FC;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border: 1px solid #EBECF0; border-radius: 12px; padding: 32px;
           width: 340px; text-align: center; box-shadow: 0 12px 32px rgba(23,43,77,.12); }}
  .badge {{ background: #E8F6FE; color: #0B6FB4; font-size: 11px; font-weight: 700;
            padding: 4px 10px; border-radius: 4px; letter-spacing: .5px; }}
  h1 {{ font-size: 18px; margin: 14px 0 4px; color: #172B4D; }}
  .amount {{ font-size: 32px; font-weight: 800; margin: 10px 0; color: #172B4D; }}
  .meta {{ color: #5E6C84; font-size: 13px; }}
  .status {{ margin-top: 18px; font-size: 14px; font-weight: 600; min-height: 20px; }}
  .ok {{ color: #037B49 }} .bad {{ color: #B3261E }}
  button {{ margin-top: 16px; width: 100%; padding: 13px; border: 0; border-radius: 4px;
            background: #0D94FB; color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; }}
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
    theme: {{ color: "#0D94FB" }},
    prefill: {{ name: "AgentPay User" }},
    handler: function (r) {{
      document.getElementById('status').textContent = 'Verifying payment…';
      fetch('/guard/payments/razorpay/callback', {{
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


@router.get("/checkout/{authorization_id}")
def checkout_page(authorization_id: str) -> Response:
    from .routes_guard import order_for_authorization

    import asyncio

    try:
        info = asyncio.run(order_for_authorization(authorization_id))
    except Exception:
        return HTMLResponse("Authorization not found or expired.", status_code=404)
    if not info.get("live"):
        return HTMLResponse(
            "This purchase runs in simulated mode (no Razorpay keys configured) — payment auto-captured.",
            media_type="text/plain",
        )
    if info.get("status") == "captured":
        return HTMLResponse(
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
    return HTMLResponse(content=html)
