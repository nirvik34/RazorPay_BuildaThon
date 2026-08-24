"""Shared AgentPay Guard MCP tool logic.

Used by both transports:
  - guard_mcp_server.py  (stdio, for Claude Desktop)
  - remote_server.py     (Streamable HTTP, for Claude web/Android via tunnel)
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
APPROVAL_TIMEOUT_S = int(os.environ.get("GUARD_APPROVAL_TIMEOUT", "180"))
POLL_INTERVAL_S = 2
PUBLIC_URL = os.environ.get("GUARD_PUBLIC_URL", "http://localhost:8002").rstrip("/")

SHOP_LINKS = {
    "amazon_in": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
}


def shop_links(query: str) -> dict:
    from urllib.parse import quote

    return {name: tpl.format(q=quote(query)) for name, tpl in SHOP_LINKS.items()}


PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "agentpay-guard", "version": "0.3.0"}

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
    {
        "name": "check_payment",
        "description": "Check the payment status of a purchase (useful after the user completes Razorpay Checkout). Optionally pass request_id; defaults to the most recent transaction.",
        "inputSchema": {
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
        },
    },
]


def http(
    method: str, path: str, payload: dict | None = None, timeout: int = 30
) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


class GuardUnavailable(Exception):
    pass


def _fmt_block(decision: dict) -> str:
    block = next(
        (rc for rc in decision.get("reasonCodes", []) if rc.get("severity") == "block"),
        {},
    )
    return (
        f"🚫 BLOCKED BY AGENTPAY GUARD — the purchase was stopped, no payment was attempted.\n"
        f"reason: {block.get('label', 'policy violation')} [{block.get('code')}]\n"
        f"Tell the user why, and do not retry this purchase."
    )


def _execute(request_id: str) -> str:
    act = http("POST", f"/guard/approvals/{request_id}/action", {"action": "accept"})
    auth_id = act["authorization"]["authorizationId"]
    pay = http(
        "POST", "/guard/payments/execute", {"authorizationId": auth_id}, timeout=60
    )
    order = pay.get("order", {})
    payment = pay.get("payment", {})

    if payment.get("status") == "captured":
        mode = (
            "SIMULATED (no Razorpay keys configured)"
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

    # Live Razorpay order created — user completes payment via real Checkout
    checkout_url = f"{PUBLIC_URL}/checkout/{auth_id}"
    return (
        f"💳 APPROVED — payment link ready. Share this with the user and ask them to open it:\n"
        f"{checkout_url}\n"
        f"(opens Razorpay Checkout — UPI/cards/netbanking; test mode shows test methods)\n"
        f"order: {order.get('id')} · authorization: {auth_id} (expires in 5 minutes)\n"
        f"After they pay, confirm with the check_payment tool for request {request_id}."
    )
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
    response: dict = {"results": hits[:8], "buy_online_search_links": shop_links(query)}
    if not hits:
        response["note"] = (
            "Not in the AgentPay catalog. Share the buy_online_search_links with the user, "
            "or pick the closest catalog product. Never invent a product_id."
        )
    return json.dumps(response)


def tool_check_payment(args: dict) -> str:
    request_id = str(args.get("request_id", "")).strip()
    if not request_id:
        txns = http("GET", "/transactions")
        rows = txns.get("transactions", [])
        if not rows:
            return "No transactions found."
        request_id = rows[0]["request"]["requestId"]
    status = http("GET", f"/agent/payment-status/{request_id}")
    payment = status.get("payment")
    request = status.get("request", {})
    lines = [
        f"request: {request_id}",
        f"product: {request.get('product')} ₹{request.get('amount')}",
        f"decision: {status.get('decision', {}).get('decision')}",
    ]
    if payment:
        lines += [
            f"payment: {payment.get('id')} — {payment.get('status')}"
            + (f" via {payment['method']}" if payment.get("method") else "")
        ]
        if payment.get("status") == "awaiting_checkout":
            lines.append("User has not completed Razorpay Checkout yet.")
    else:
        lines.append("No payment attempted yet.")
    return "\n".join(lines)


def _wait_for_user(request_id: str) -> dict | None:
    deadline = time.time() + APPROVAL_TIMEOUT_S
    while time.time() < deadline:
        status = http("GET", f"/agent/payment-status/{request_id}")
        if status.get("resolution"):
            return status
        time.sleep(POLL_INTERVAL_S)
    return None


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
        return (
            f"❌ Unknown product_id '{product_id}'. Call search_products first.\n"
            f"If the user wants something outside the catalog, share these links instead of purchasing:\n"
            + json.dumps(shop_links(product_id.replace("-", " ")), indent=2)
        )

    try:
        decision = http(
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
    except urllib.error.URLError as exc:
        raise GuardUnavailable(f"AgentPay Guard unreachable at {API}: {exc}") from exc

    rid = decision["requestId"]
    outcome = decision["decision"]

    if outcome == "BLOCK":
        return _fmt_block(decision)

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
    return json.dumps(http("GET", "/policies"), indent=2)


def dispatch(name: str, args: dict) -> str:
    if name == "search_products":
        return tool_search(args)
    if name == "purchase":
        return tool_purchase(args)
    if name == "get_guard_policy":
        return tool_policy({})
    if name == "check_payment":
        return tool_check_payment(args)
    return f"Unknown tool: {name}"


def register_agent() -> None:
    try:
        http(
            "POST",
            "/agent/register",
            {"agentId": AGENT_ID, "name": "Claude (remote MCP)", "trustScore": 92},
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[agentpay] warning: could not reach Guard at {API}: {exc}",
            file=sys.stderr,
        )
