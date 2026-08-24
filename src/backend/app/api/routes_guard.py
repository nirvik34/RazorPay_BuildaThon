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
from ..services.razorpay_service import RazorpayError, capture_payment, create_order

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


@router.get("/pending")
async def pending() -> list[dict]:
    state = store.snapshot()
    out: list[dict] = []
    for request_id, decision in state["decisions"].items():
        if (
            decision["decision"] == "USER_APPROVAL"
            and decision.get("authorizationId") is None
        ):
            rec = {
                "decision": decision,
                "request": state["requests"][request_id],
            }
            if request_id not in [a["requestId"] for a in _resolved(state)]:
                out.append(rec)
    return out


def _resolved(state: dict) -> list[dict]:
    return [e for e in state.get("resolutions", [])]


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


@router.post("/payments/execute")
async def execute(payload: ExecuteIn) -> dict:
    with LOCK:
        state = store.state
        auth = state["authorizations"].get(payload.authorizationId)
        if not auth:
            raise HTTPException(status_code=404, detail={"code": "AUTH_NOT_FOUND"})
        if auth["status"] == "USED":
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
        payment = await capture_payment(order)
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
        state["payments"][payment["id"]] = {
            **payment,
            "authorizationId": payload.authorizationId,
            "requestId": request_id,
        }
        state["audit"][request_id].append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": now_iso(),
                "label": "Payment captured"
                if payment.get("status") == "captured"
                else "Payment processing",
            }
        )
        store.save()

    broadcast_sync(
        "payment_update",
        {
            "requestId": request_id,
            "paymentId": payment["id"],
            "status": payment.get("status"),
        },
    )
    return {"ok": True, "order": order, "payment": payment}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request, x_razorpay_signature: str | None = Header(default=None)
) -> dict:
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
    with LOCK:
        state = store.state
        record = state.get("payments", {}).get(payment_id)
        if record:
            record["status"] = entity.get("status", record["status"])
            store.save()
    return {"ok": True}


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
