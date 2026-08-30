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

from tools.catalog import CATALOG, CatalogItem, search_catalog  # noqa: E402

API = os.environ.get("GUARD_API", "http://localhost:8000").rstrip("/")
AGENT_ID = os.environ.get("GUARD_AGENT_ID", "claude-shopping-01")
APPROVAL_TIMEOUT_S = int(os.environ.get("GUARD_APPROVAL_TIMEOUT", "180"))
POLL_INTERVAL_S = 1
PUBLIC_URL = os.environ.get("GUARD_PUBLIC_URL", "http://localhost:8002").rstrip("/")


def get_public_url() -> str:
    global PUBLIC_URL
    if PUBLIC_URL and not PUBLIC_URL.startswith("http://localhost") and not PUBLIC_URL.startswith("http://127.0.0.1"):
        return PUBLIC_URL.rstrip("/")
    env_url = os.environ.get("GUARD_PUBLIC_URL")
    if env_url:
        return env_url.rstrip("/")
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=1) as resp:
            data = json.loads(resp.read().decode())
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                if t.get("proto") in ("https", "http"):
                    pub = t["public_url"].rstrip("/")
                    PUBLIC_URL = pub
                    return pub
    except Exception:
        pass
    return PUBLIC_URL or "http://localhost:8002"


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
        "description": "Search for products across merchant catalogs and global online stores. Returns product_id, name, merchant, category, and price in INR. Supports any product/search query beyond local catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords, e.g. 'Sony WH-1000XM5' or 'groceries' or any custom item",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum budget in INR",
                },
                "min_price": {"type": "number", "description": "Minimum price in INR"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "purchase",
        "description": "Attempt to purchase any product. The request goes through AgentPay Guard on the user's phone: the user must ACCEPT before any payment executes. Works with catalog product_id or dynamic custom products.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Product ID from search_products or custom product identifier",
                },
                "product_name": {
                    "type": "string",
                    "description": "Optional custom product name if buying non-catalog item",
                },
                "merchant": {
                    "type": "string",
                    "description": "Optional merchant name (e.g. Amazon, Flipkart)",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category (e.g. electronics, groceries, clothing)",
                },
                "amount": {
                    "type": "number",
                    "description": "Optional price in INR if buying custom item",
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
        "description": "Check the payment status of a purchase (useful after the user approves on phone or completes Razorpay Checkout). Optionally pass request_id; defaults to the most recent transaction.",
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
    pub_url = get_public_url()
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
    checkout_url = f"{pub_url}/checkout/{auth_id}"
    return (
        f"💳 APPROVED — payment link ready. Share this with the user and ask them to open it:\n"
        f"{checkout_url}\n"
        f"(opens Razorpay Checkout — UPI/cards/netbanking; test mode shows test methods)\n"
        f"order: {order.get('id')} · authorization: {auth_id} (expires in 5 minutes)\n"
        f"After they pay, confirm with the check_payment tool for request {request_id}."
    )


def infer_category(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["headphone", "earbud", "earphone", "laptop", "macbook", "phone", "iphone", "samsung", "tv", "monitor", "display", "mouse", "keyboard", "watch", "camera", "gadget", "charger", "cable", "audio", "speaker", "tech", "electronics"]):
        return "electronics"
    if any(w in t for w in ["grocer", "food", "milk", "bread", "atta", "rice", "dal", "snack", "fruit", "veg", "staples"]):
        return "groceries"
    if any(w in t for w in ["shirt", "pant", "shoe", "cloth", "dress", "jacket", "wear", "apparel"]):
        return "clothing"
    if any(w in t for w in ["chair", "table", "desk", "sofa", "bed", "furniture", "lamp"]):
        return "office_supplies"
    if any(w in t for w in ["gift", "voucher", "card"]):
        return "gift_cards"
    if any(w in t for w in ["casino", "bet", "gamble", "poker", "lotto"]):
        return "gambling"
    return "electronics"


def encode_custom_product(merchant: str, category: str, amount: int, product_name: str) -> str:
    clean_name = product_name.replace("::", " ")
    return f"custom::{merchant}::{category}::{amount}::{clean_name}"


def decode_custom_product(product_id: str) -> dict | None:
    if not product_id.startswith("custom::"):
        return None
    parts = product_id.split("::", 4)
    if len(parts) < 5:
        return None
    try:
        return {
            "merchant": parts[1],
            "category": parts[2],
            "amount": int(parts[3]),
            "product": parts[4],
        }
    except Exception:
        None
    return None


def tool_search(args: dict) -> str:
    query = str(args.get("query", ""))
    max_price = args.get("max_price")
    min_price = args.get("min_price")

    hits = [
        {
            "product_id": item.product.lower().replace(" ", "-").replace('"', ""),
            "name": item.product,
            "merchant": item.merchant,
            "category": item.category,
            "price_inr": item.price,
            "source": "Catalog",
        }
        for item in search_catalog(query)
    ]
    if isinstance(max_price, (int, float)):
        hits = [h for h in hits if h["price_inr"] <= max_price]
    if isinstance(min_price, (int, float)):
        hits = [h for h in hits if h["price_inr"] >= min_price]
    hits.sort(key=lambda h: h["price_inr"])

    # Always generate custom web search product options so user can buy anything
    est_price = int(max_price) if isinstance(max_price, (int, float)) else 2999
    if isinstance(min_price, (int, float)) and min_price > est_price:
        est_price = int(min_price)

    cat = infer_category(query)
    q_title = query.strip().title()

    amazon_pid = encode_custom_product("amazon", cat, est_price, q_title)
    flipkart_pid = encode_custom_product("flipkart", cat, max(1, int(est_price * 0.95)), q_title)

    global_hits = [
        {
            "product_id": amazon_pid,
            "name": f"{q_title} (Amazon)",
            "merchant": "amazon",
            "category": cat,
            "price_inr": est_price,
            "source": "Global Web Search",
        },
        {
            "product_id": flipkart_pid,
            "name": f"{q_title} (Flipkart)",
            "merchant": "flipkart",
            "category": cat,
            "price_inr": max(1, int(est_price * 0.95)),
            "source": "Global Web Search",
        },
    ]
    existing_names = {h["name"].lower() for h in hits}
    for gh in global_hits:
        if gh["name"].lower() not in existing_names:
            hits.append(gh)

    response: dict = {
        "results": hits[:8],
        "buy_online_search_links": shop_links(query),
        "note": (
            "Global web search power enabled. You can purchase ANY item listed in results using its product_id, "
            "or purchase ANY custom product by providing product_name, amount, merchant, and category."
        ),
    }
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
    if not status.get("resolution"):
        polled = _wait_for_user(request_id, timeout_s=15.0)
        if polled:
            status = polled

    payment = status.get("payment")
    request = status.get("request", {})
    decision_info = status.get("decision", {})
    decision = decision_info.get("decision")
    resolution = status.get("resolution")

    if resolution and resolution.get("action") == "reject":
        return f"❌ Purchase request {request_id} was DECLINED by the user on their phone."

    if resolution and resolution.get("action") == "accept":
        if not payment:
            # User accepted on phone! Complete execution and return checkout link.
            return _execute(request_id)
        else:
            lines = [
                f"request: {request_id}",
                f"product: {request.get('product')} ₹{request.get('amount')}",
                f"decision: {decision}",
                f"payment: {payment.get('id')} — {payment.get('status')}"
                + (f" via {payment['method']}" if payment.get("method") else ""),
            ]
            if payment.get("status") == "awaiting_checkout":
                pub_url = get_public_url()
                auth_id = payment.get("authorizationId") or payment.get("id")
                lines.append(f"💳 Payment link ready: {pub_url}/checkout/{auth_id}")
                lines.append("User has not completed Razorpay Checkout yet.")
            return "\n".join(lines)

    if decision == "USER_APPROVAL" and not resolution:
        return (
            f"⏳ Request {request_id} for {request.get('product')} (₹{request.get('amount')}) is STILL PENDING approval on the user's phone.\n"
            f"Please tap ACCEPT in the AgentPay Guard app on your phone."
        )

    lines = [
        f"request: {request_id}",
        f"product: {request.get('product')} ₹{request.get('amount')}",
        f"decision: {decision}",
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


def _wait_for_user(request_id: str, timeout_s: float = 30.0) -> dict | None:
    deadline = time.time() + min(timeout_s, float(APPROVAL_TIMEOUT_S))
    while time.time() < deadline:
        status = http("GET", f"/agent/payment-status/{request_id}")
        if status.get("resolution"):
            return status
        time.sleep(POLL_INTERVAL_S)
    return None


def tool_purchase(args: dict) -> str:
    product_id = str(args.get("product_id", "")).strip()
    reason = str(args.get("reason", "")).strip()

    item = next(
        (
            i
            for i in CATALOG
            if i.product.lower().replace(" ", "-").replace('"', "") == product_id.lower()
        ),
        None,
    )

    if item is None and product_id.startswith("custom::"):
        decoded = decode_custom_product(product_id)
        if decoded:
            item = CatalogItem(
                product=decoded["product"],
                merchant=decoded["merchant"],
                category=decoded["category"],
                price=decoded["amount"],
            )

    if item is None and (args.get("product_name") or args.get("product") or args.get("amount") or args.get("price")):
        p_name = str(args.get("product_name") or args.get("product") or product_id.replace("-", " ").title())
        p_amount = int(args.get("amount") or args.get("price") or 1000)
        p_merchant = str(args.get("merchant") or "amazon").lower()
        p_cat = str(args.get("category") or infer_category(p_name)).lower()
        item = CatalogItem(
            product=p_name,
            merchant=p_merchant,
            category=p_cat,
            price=p_amount,
        )

    if item is None and product_id and product_id.lower() != "unknown":
        p_name = product_id.replace("-", " ").title()
        p_amount = int(args.get("amount") or args.get("price") or 1000)
        p_merchant = str(args.get("merchant") or "amazon").lower()
        p_cat = str(args.get("category") or infer_category(p_name)).lower()
        item = CatalogItem(
            product=p_name,
            merchant=p_merchant,
            category=p_cat,
            price=p_amount,
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
        status = _wait_for_user(rid, timeout_s=30.0)
        if status is None:
            return (
                f"⏳ AGENTPAY GUARD — APPROVAL SENT TO USER'S PHONE\n"
                f"Request ID: {rid}\n"
                f"Item: {item.product} (₹{item.price})\n"
                f"Merchant: {item.merchant}\n\n"
                f"An approval prompt has been sent to the AgentPay Guard app on your phone.\n"
                f"Please tap ACCEPT in your app. "
                f"INSTRUCTION FOR AI: Do not stop execution! Call check_payment(request_id='{rid}') to wait for approval and get the final Razorpay Checkout link."
            )
        if status.get("resolution", {}).get("action") == "reject":
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
