#!/usr/bin/env python3
"""AgentPay Guard — MCP server for real AI shopping agents.

Connect Claude Desktop (or any MCP client) to AgentPay Guard. When the AI
decides to buy something during a chat, the purchase goes through the Guard:
the user's phone gets an approval notification, and only an explicit ACCEPT
lets the Razorpay payment execute. Malicious/policy-violating purchases are
blocked with the reason returned to the agent.

Run:  python3 guard_mcp_server.py        (stdio, newline-delimited JSON-RPC 2.0)
Env:  GUARD_API=http://localhost:8000
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from tools.catalog import CATALOG, search_catalog  # noqa: E402

API = os.environ.get("GUARD_API", "http://localhost:8000").rstrip("/")
AGENT_ID = os.environ.get("GUARD_AGENT_ID", "claude-shopping-01")
APPROVAL_TIMEOUT_S = 180
POLL_INTERVAL_S = 2

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "search_products",
        "description": "Search the merchant catalog before buying. Returns product_id, name, merchant, category and price in INR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords, e.g. 'headphones' or 'groceries'",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "purchase",
        "description": "Attempt to purchase a product. The request goes through AgentPay Guard on the user's phone: the user must ACCEPT before any payment executes, and policy-violating purchases are blocked automatically. Always search_products first and use the exact product_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Exact product_id from search_products",
                },
                "reason": {
                    "type": "string",
                    "description": "Why you are buying this for the user",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "get_guard_policy",
        "description": "Fetch the user's current spending policy (limits, blocked categories, approval rules) so you can respect it proactively.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _http(method: str, path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _fmt_reasons(decision: dict) -> str:
    return ", ".join(rc.get("code", "") for rc in decision.get("reasonCodes", []))


def tool_search(args: dict) -> str:
    query = str(args.get("query", ""))
    hits = [
        {
            "product_id": item.product.lower().replace(" ", "-").replace('"', ""),
            "name": item.product,
            "merchant": item.merchant,
            "category": item.category,
            "price_inr": item.price,
        }
        for item in search_catalog(query)
    ]
    if not hits:
        return json.dumps(
            {"results": [], "note": "No products matched. Try broader keywords."}
        )
    return json.dumps({"results": hits[:8]})


def _wait_for_user(request_id: str) -> dict | None:
    deadline = time.time() + APPROVAL_TIMEOUT_S
    while time.time() < deadline:
        status = _http("GET", f"/agent/payment-status/{request_id}")
        if status.get("resolution"):
            return status
        time.sleep(POLL_INTERVAL_S)
    return None


def _execute(request_id: str) -> str:
    act = _http("POST", f"/guard/approvals/{request_id}/action", {"action": "accept"})
    auth_id = act["authorization"]["authorizationId"]
    pay = _http("POST", "/guard/payments/execute", {"authorizationId": auth_id})
    order = pay.get("order", {})
    payment = pay.get("payment", {})
    mode = (
        "SIMULATED (set Razorpay test keys in backend .env for real orders)"
        if payment.get("simulated")
        else "LIVE Razorpay"
    )
    return (
        f"✅ PAYMENT SUCCESSFUL\n"
        f"order: {order.get('id')}\n"
        f"payment: {payment.get('id')} ({payment.get('status')})\n"
        f"authorization: {auth_id} (single-use, now consumed)\n"
        f"mode: {mode}"
    )


def tool_purchase(args: dict) -> str:
    product_id = str(args.get("product_id", "")).lower()
    reason = str(args.get("reason", "")).strip()
    item = next(
        (
            i
            for i in CATALOG
            if i.product.lower().replace(" ", "-").replace('"', "") == product_id
        ),
        None,
    )
    if item is None:
        return f"❌ Unknown product_id '{product_id}'. Call search_products first."

    decision = _http(
        "POST",
        "/agent/payment-request",
        {
            "agentId": AGENT_ID,
            "merchant": item.merchant,
            "product": item.product,
            "amount": item.price,
            "currency": "INR",
            "category": item.category,
        },
    )
    rid = decision["requestId"]
    outcome = decision["decision"]

    if outcome == "BLOCK":
        block = next(
            (rc for rc in decision["reasonCodes"] if rc.get("severity") == "block"), {}
        )
        return (
            f"🚫 BLOCKED BY AGENTPAY GUARD — the purchase was stopped, no payment was attempted.\n"
            f"reason: {block.get('label', 'policy violation')} [{block.get('code')}]\n"
            f"Tell the user why, and do not retry this purchase."
        )

    if outcome == "USER_APPROVAL":
        print(
            f"[agentpay] approval request sent to phone: {item.product} ₹{item.price} ({rid})",
            file=sys.stderr,
        )
        status = _wait_for_user(rid)
        if status is None:
            return (
                f"⏳ The user did not respond within {APPROVAL_TIMEOUT_S}s. "
                f"The purchase is still pending in AgentPay Guard — no payment was made."
            )
        if status["resolution"].get("action") == "reject":
            return (
                "❌ The user DECLINED this purchase in AgentPay Guard. "
                "No payment was attempted. Do not retry without asking the user first."
            )

    return _execute(rid) + (f"\nyour stated reason: {reason}" if reason else "")


def tool_policy(_: dict) -> str:
    policies = _http("GET", "/policies")
    return json.dumps(policies, indent=2)


def dispatch(name: str, args: dict) -> str:
    if name == "search_products":
        return tool_search(args)
    if name == "purchase":
        return tool_purchase(args)
    if name == "get_guard_policy":
        return tool_policy({})
    return f"Unknown tool: {name}"


def handle(req: dict) -> dict | None:
    method = req.get("method", "")
    msg_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentpay-guard", "version": "0.2.0"},
            },
        }
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params", {})
        try:
            text = dispatch(params.get("name", ""), params.get("args") or {})
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        except urllib.error.URLError as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"AgentPay Guard unreachable at {API}: {exc}. Is the backend running?",
                        }
                    ],
                    "isError": True,
                },
            }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    try:
        _http(
            "POST",
            "/agent/register",
            {"agentId": AGENT_ID, "name": "Claude Desktop (MCP)", "trustScore": 92},
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[agentpay] warning: could not reach Guard at {API}: {exc}",
            file=sys.stderr,
        )

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
