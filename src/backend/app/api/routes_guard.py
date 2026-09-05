from __future__ import annotations

import hmac
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..state import LOCK, new_id, now_iso, store
from ..ws import broadcast_sync
from ..services.razorpay_service import (
    RazorpayError,
    capture_payment_by_id,
    create_order,
    fetch_payment,
    finalize_payment,
)

router = APIRouter(prefix="/guard", tags=["guard"])


class DecisionAction(BaseModel):
    action: str


class ExecuteIn(BaseModel):
    authorizationId: str


def _request(state: dict, request_id: str) -> dict:
    req = state["requests"].get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail={"code": "REQUEST_NOT_FOUND"})
    return req


PENDING_TTL_SECONDS = 300  # scoped authorizations live 5 minutes; approvals match


@router.get("/pending")
async def pending() -> list[dict]:
    """Undecided approval requests, with automatic expiry after the 5-min window.

    Expired requests are marked resolved server-side so they never re-appear,
    and the agent's purchase poll sees a definitive 'expired' outcome.
    """
    state = store.snapshot()
    now = datetime.now(timezone.utc)
    resolved_ids = {r["requestId"] for r in state.get("resolutions", [])}
    out: list[dict] = []
    expired: list[str] = []

    for request_id, decision in state["decisions"].items():
        if decision["decision"] != "USER_APPROVAL":
            continue
        if decision.get("authorizationId") is not None:
            continue
        if request_id in resolved_ids:
            continue
        req = state["requests"].get(request_id)
        if not req:
            continue
        try:
            ts = datetime.fromisoformat(req["timestamp"])
        except ValueError:
            continue
        if (now - ts).total_seconds() > PENDING_TTL_SECONDS:
            expired.append(request_id)
            continue
        out.append({"decision": decision, "request": req})

    if expired:
        with LOCK:
            live = store.state
            for rid in expired:
                live.setdefault("resolutions", []).append(
                    {"requestId": rid, "action": "expire", "at": now_iso()}
                )
                live["audit"].setdefault(rid, []).append(
                    {
                        "eventId": new_id("evt"),
                        "requestId": rid,
                        "at": now_iso(),
                        "label": "Approval window elapsed",
                        "detail": "Auto-expired after 5 minutes without a decision",
                    }
                )
            store.save()
        broadcast_sync("approvals_expired", {"requestIds": expired})

    return out


@router.post("/approvals/{request_id}/action")
async def approval_action(request_id: str, payload: DecisionAction) -> dict:
    action = payload.action.lower()
    if action not in ("accept", "reject"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_ACTION",
                "message": "action must be accept or reject",
            },
        )

    with LOCK:
        state = store.state
        req = _request(state, request_id)
        decision = state["decisions"][request_id]
        at = now_iso()

        if action == "accept":
            authorization_id = f"auth_{uuid.uuid4().hex[:6]}"
            expires = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
            auth = {
                "authorizationId": authorization_id,
                "requestId": request_id,
                "agentId": req["agentId"],
                "merchant": req["merchant"],
                "product": req["product"],
                "amount": req["amount"],
                "currency": req["currency"],
                "intentId": req.get("intentId"),
                "expiresAt": expires,
                "status": "AUTHORIZED",
                "issuedAt": at,
            }
            state["authorizations"][authorization_id] = auth
            decision["authorizationId"] = authorization_id
            events = [
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": at,
                    "label": "User accepted",
                },
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": at,
                    "label": "Authorization issued",
                    "detail": authorization_id,
                },
            ]
            result: dict = {"ok": True, "decision": "AUTHORIZED", "authorization": auth}
        else:
            events = [
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": at,
                    "label": "User rejected transaction",
                },
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": at,
                    "label": "Authorization denied",
                },
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": at,
                    "label": "Agent informed",
                    "detail": "Structured denial returned",
                },
            ]
            result = {"ok": True, "decision": "DENIED"}

        state.setdefault("resolutions", []).append(
            {"requestId": request_id, "action": action, "at": at}
        )
        state["audit"][request_id] = state["audit"].get(request_id, []) + events
        store.save()

    broadcast_sync("approval_decided", {"requestId": request_id, "action": action})
    return result


async def execute_authorization(authorization_id: str, allow_idempotent: bool = False) -> dict:
    with LOCK:
        state = store.state
        auth = state["authorizations"].get(authorization_id)
        if not auth:
            raise HTTPException(status_code=404, detail={"code": "AUTH_NOT_FOUND"})
        if auth["status"] == "USED":
            if allow_idempotent:
                existing_payment = next(
                    (p for p in state.get("payments", {}).values() if p.get("authorizationId") == authorization_id),
                    None,
                )
                if existing_payment:
                    return {"ok": True, "order": {}, "payment": existing_payment}
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ALREADY_USED",
                    "message": "Scoped authorization is single-use",
                },
            )
        if datetime.fromisoformat(auth["expiresAt"]) < datetime.now(timezone.utc):
            auth["status"] = "EXPIRED"
            store.save()
            raise HTTPException(
                status_code=410,
                detail={"code": "EXPIRED", "message": "Authorization window elapsed"},
            )
        auth["status"] = "USED"
        request_id = auth["requestId"]
        state["audit"].setdefault(request_id, []).append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": now_iso(),
                "label": "Payment initiated",
                "detail": "Razorpay order",
            }
        )
        store.save()

    try:
        order = await create_order(auth)
        payment = await finalize_payment(order)
    except RazorpayError as exc:
        with LOCK:
            state = store.state
            state["audit"][request_id].append(
                {
                    "eventId": new_id("evt"),
                    "requestId": request_id,
                    "at": now_iso(),
                    "label": "Payment failed",
                    "detail": str(exc),
                }
            )
            store.save()
        raise HTTPException(
            status_code=502, detail={"code": "PAYMENT_FAILED", "message": str(exc)}
        ) from exc

    with LOCK:
        state = store.state
        state["payments"] = state.get("payments", {})
        payment_key = payment.get("id") or f"pending_{authorization_id}"
        payment["authorizationId"] = authorization_id
        payment["requestId"] = request_id
        state["payments"][payment_key] = payment
        state["audit"][request_id].append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": now_iso(),
                "label": "Payment captured"
                if payment.get("status") == "captured"
                else "Payment initiated — awaiting checkout",
                "detail": order.get("id"),
            }
        )
        store.save()

    broadcast_sync(
        "payment_update",
        {
            "requestId": request_id,
            "paymentId": payment.get("id"),
            "status": payment.get("status"),
        },
    )
    return {"ok": True, "order": order, "payment": payment}


@router.post("/payments/execute")
async def execute(payload: ExecuteIn) -> dict:
    return await execute_authorization(payload.authorizationId)



class CheckoutConfirmIn(BaseModel):
    payment_id: str
    order_id: str
    authorization_id: str


@router.post("/payments/razorpay/callback")
async def razorpay_checkout_callback(payload: CheckoutConfirmIn) -> dict:
    """Called by the checkout page after the user completes Razorpay payment.

    Verifies the payment server-side against the Razorpay API (never trusts the
    browser), then captures it if authorized.
    """
    with LOCK:
        state = store.state
        auth = state["authorizations"].get(payload.authorization_id)
        if not auth:
            raise HTTPException(status_code=404, detail={"code": "AUTH_NOT_FOUND"})
        request_id = auth["requestId"]

    try:
        remote = await fetch_payment(payload.payment_id)
    except RazorpayError as exc:
        raise HTTPException(
            status_code=502, detail={"code": "VERIFY_FAILED", "message": str(exc)}
        ) from exc

    if remote.get("order_id") != payload.order_id:
        raise HTTPException(status_code=400, detail={"code": "ORDER_MISMATCH"})

    if remote.get("status") == "authorized":
        remote = await capture_payment_by_id(remote["id"], remote["amount"])

    with LOCK:
        state = store.state
        state["payments"][remote["id"]] = {
            **remote,
            "authorizationId": payload.authorization_id,
            "requestId": request_id,
        }
        state["audit"][request_id].append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": now_iso(),
                "label": f"Payment {remote['status']}",
                "detail": f"{remote['id']} via {remote.get('method', 'razorpay')}",
            }
        )
        store.save()

    broadcast_sync(
        "payment_update",
        {
            "requestId": request_id,
            "paymentId": remote["id"],
            "status": remote.get("status"),
        },
    )
    return {
        "ok": True,
        "payment": {
            "id": remote["id"],
            "status": remote["status"],
            "method": remote.get("method"),
        },
    }


@router.get("/payments/order/{authorization_id}")
async def order_for_authorization(authorization_id: str) -> dict:
    """Public data needed to render the Razorpay Checkout page (key id is publishable)."""
    state = store.snapshot()
    auth = state["authorizations"].get(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail={"code": "AUTH_NOT_FOUND"})
    payment = next(
        (
            p
            for p in state.get("payments", {}).values()
            if p.get("authorizationId") == authorization_id
        ),
        None,
    )
    return {
        "orderId": payment.get("order_id") if payment else None,
        "keyId": settings.razorpay_key_id,
        "live": settings.razorpay_live,
        "amount": payment.get("amount", auth["amount"] * 100)
        if payment
        else auth["amount"] * 100,
        "currency": "INR",
        "product": auth["product"],
        "merchant": auth["merchant"],
        "status": payment.get("status", "created") if payment else "created",
        "requestId": auth["requestId"],
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request, x_razorpay_signature: str | None = Header(default=None)
) -> dict:
    """Safety net for the JS checkout: if the user pays but the browser confirm
    never fires (tab closed, crash), Razorpay's `payment.authorized` webhook
    triggers the server-side capture here instead."""
    body = await request.body()
    if settings.razorpay_webhook_secret:
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not x_razorpay_signature or not hmac.compare_digest(
            expected, x_razorpay_signature
        ):
            raise HTTPException(status_code=400, detail={"code": "BAD_SIGNATURE"})
    data = await request.json()
    entity = data.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = entity.get("id")
    event = data.get("event", "")
    if not payment_id:
        return {"ok": True, "ignored": "no payment entity"}

    with LOCK:
        state = store.state
        record = state.get("payments", {}).get(payment_id)
    if not record:
        return {"ok": True, "ignored": "unknown payment (not an AgentPay order)"}

    request_id = record.get("requestId")

    if event == "payment.authorized" and record.get("status") not in ("captured",):
        try:
            remote = await capture_payment_by_id(payment_id, entity.get("amount", 0))
        except RazorpayError as exc:
            with LOCK:
                state = store.state
                state["audit"].setdefault(request_id, []).append(
                    {
                        "eventId": new_id("evt"),
                        "requestId": request_id,
                        "at": now_iso(),
                        "label": "Webhook capture failed",
                        "detail": str(exc),
                    }
                )
                store.save()
            raise HTTPException(
                status_code=502, detail={"code": "CAPTURE_FAILED", "message": str(exc)}
            ) from exc
    else:
        remote = entity

    with LOCK:
        state = store.state
        state["payments"][remote.get("id", payment_id)] = {
            **record,
            **remote,
            "requestId": request_id,
        }
        state["audit"].setdefault(request_id, []).append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": now_iso(),
                "label": f"Payment {remote.get('status')} (webhook)",
                "detail": f"{event} · {payment_id}",
            }
        )
        store.save()

    broadcast_sync(
        "payment_update",
        {
            "requestId": request_id,
            "paymentId": payment_id,
            "status": remote.get("status"),
        },
    )
    return {"ok": True, "event": event, "status": remote.get("status")}


@router.post("/agents/{agent_id}/freeze")
async def freeze(agent_id: str) -> dict:
    with LOCK:
        agent = store.state["agents"].get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND"})
        agent["status"] = "FROZEN"
        store.save()
    broadcast_sync("agent_frozen", {"agentId": agent_id})
    return {"ok": True, "agentId": agent_id, "status": "FROZEN"}


@router.post("/agents/{agent_id}/unfreeze")
async def unfreeze(agent_id: str) -> dict:
    with LOCK:
        agent = store.state["agents"].get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND"})
        agent["status"] = "ACTIVE"
        store.save()
    return {"ok": True, "agentId": agent_id, "status": "ACTIVE"}


@router.post("/agents/{agent_id}/revoke")
async def revoke(agent_id: str) -> dict:
    with LOCK:
        agent = store.state["agents"].get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND"})
        agent["status"] = "REVOKED"
        store.save()
    return {"ok": True, "agentId": agent_id, "status": "REVOKED"}
