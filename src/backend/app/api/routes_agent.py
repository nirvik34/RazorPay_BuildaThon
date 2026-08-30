from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..engine import evaluate_request
from ..state import LOCK, new_id, now_iso, store
from ..ws import broadcast_sync

router = APIRouter(prefix="/agent", tags=["agent"])


class PaymentRequestIn(BaseModel):
    requestId: Optional[str] = None
    agentId: str
    intentId: Optional[str] = None
    merchant: str
    product: str
    amount: int = Field(gt=0)
    currency: str = "INR"
    category: str
    sessionId: Optional[str] = None


class RegisterAgentIn(BaseModel):
    agentId: str
    name: str
    trustScore: int = 70
    policyId: str = "pol_default"


class IntentIn(BaseModel):
    intentId: Optional[str] = None
    goal: str
    category: str
    budget: int


def _history(state: dict) -> list[dict]:
    rows: list[dict] = []
    payments = state.get("payments", {})
    for req_id, decision in state["decisions"].items():
        req = state["requests"].get(req_id)
        if not req:
            continue
        resolution = next(
            (r for r in state.get("resolutions", []) if r["requestId"] == req_id), None
        )
        captured = any(
            p.get("requestId") == req_id and p.get("status") == "captured"
            for p in payments.values()
        )
        if decision["decision"] == "BLOCK":
            outcome = "NOT_ATTEMPTED"
        elif captured:
            outcome = "CAPTURED"
        elif resolution and resolution["action"] == "reject":
            outcome = "DENIED"
        else:
            outcome = "NOT_ATTEMPTED"
        rows.append({"request": req, "decision": decision, "outcome": outcome})
    return rows


@router.post("/register")
async def register_agent(payload: RegisterAgentIn) -> dict:
    with LOCK:
        state = store.state
        state["agents"][payload.agentId] = {
            "agentId": payload.agentId,
            "name": payload.name,
            "ownerId": "user_001",
            "status": "ACTIVE",
            "trustScore": payload.trustScore,
            "riskState": "NORMAL",
            "policyId": payload.policyId,
            "createdAt": now_iso(),
        }
        store.save()
    broadcast_sync("agent_registered", {"agentId": payload.agentId})
    return {"ok": True, "agentId": payload.agentId}


@router.post("/intent")
async def create_intent(agentId: str, payload: IntentIn) -> dict:
    with LOCK:
        state = store.state
        intent_id = payload.intentId or f"intent_{uuid.uuid4().hex[:3]}"
        state["intents"][intent_id] = {
            "intentId": intent_id,
            "agentId": agentId,
            "goal": payload.goal,
            "category": payload.category,
            "budget": payload.budget,
            "currency": "INR",
            "createdAt": now_iso(),
            "expiresAt": now_iso(),
        }
        store.save()
    return {"intentId": intent_id}


import asyncio
import os

@router.post("/payment-request")
async def payment_request(
    payload: PaymentRequestIn,
    wait_seconds: int = 15,
    x_agent_key: str | None = Header(default=None),
) -> dict:
    snapshot = store.snapshot()
    agent_id = payload.agentId

    if agent_id not in snapshot["agents"]:
        with LOCK:
            store.state["agents"][agent_id] = {
                "agentId": agent_id,
                "name": f"Agent {agent_id}",
                "ownerId": "user_001",
                "status": "ACTIVE",
                "trustScore": 70,
                "riskState": "NORMAL",
                "policyId": "pol_default",
                "createdAt": now_iso(),
            }
            store.save()
        snapshot = store.snapshot()

    request_id = payload.requestId or f"req_{uuid.uuid4().hex[:6]}"
    request = {
        "requestId": request_id,
        "agentId": agent_id,
        "intentId": payload.intentId,
        "merchant": payload.merchant.lower(),
        "product": payload.product,
        "amount": int(round(payload.amount)),
        "currency": payload.currency,
        "category": payload.category or "general",
        "sessionId": payload.sessionId or f"sess_{uuid.uuid4().hex[:8]}",
        "timestamp": now_iso(),
    }

    agent = snapshot["agents"][agent_id]
    policy = snapshot["policies"].get(
        agent["policyId"], snapshot["policies"]["pol_default"]
    )

    decision = evaluate_request(
        request, agent, policy, _history(snapshot), snapshot["intents"]
    )
    decision.pop("riskLevel", None)
    decision.pop("riskSignals", None)
    decision.pop("circumvention", None)
    decision["requestId"] = request_id

    events = [
        {
            "eventId": new_id("evt"),
            "requestId": request_id,
            "at": request["timestamp"],
            "label": "Payment request received",
            "detail": request["product"],
        },
        {
            "eventId": new_id("evt"),
            "requestId": request_id,
            "at": request["timestamp"],
            "label": "Agent authenticated",
            "detail": agent_id,
        },
        {
            "eventId": new_id("evt"),
            "requestId": request_id,
            "at": request["timestamp"],
            "label": "Policy evaluated",
            "detail": f"v{decision['policyVersion']}",
        },
        {
            "eventId": new_id("evt"),
            "requestId": request_id,
            "at": request["timestamp"],
            "label": "Risk assessed",
            "detail": f"{decision['riskScore']}/100",
        },
    ]
    if decision["decision"] == "BLOCK":
        block_reason = next(
            (r for r in decision["reasonCodes"] if r["severity"] == "block"), None
        )
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": block_reason["label"] if block_reason else "Blocked by policy",
                "detail": block_reason["code"] if block_reason else None,
            }
        )
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": "No approval requested",
            }
        )
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": "Agent informed",
                "detail": "Structured denial returned",
            }
        )
    elif decision["decision"] == "USER_APPROVAL":
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": "User notified",
            }
        )
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": "Awaiting user decision",
            }
        )
    else:
        events.append(
            {
                "eventId": new_id("evt"),
                "requestId": request_id,
                "at": request["timestamp"],
                "label": "Auto-authorized within policy",
            }
        )

    with LOCK:
        live = store.state
        live["requests"][request_id] = request
        live["decisions"][request_id] = decision
        live["audit"][request_id] = live["audit"].get(request_id, []) + events
        store.save()

    broadcast_sync(
        "new_request",
        {
            "requestId": request_id,
            "agentId": agent_id,
            "product": request["product"],
            "amount": request["amount"],
            "decision": decision["decision"],
        },
    )

    # If user approval is required, wait up to wait_seconds for approval on phone before returning
    if decision["decision"] == "USER_APPROVAL" and wait_seconds > 0:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + min(wait_seconds, 30)
        while loop.time() < deadline:
            await asyncio.sleep(1.0)
            current_state = store.snapshot()
            resolution = next(
                (r for r in current_state.get("resolutions", []) if r["requestId"] == request_id),
                None,
            )
            if resolution:
                if resolution["action"] == "accept":
                    auth_id = current_state["decisions"].get(request_id, {}).get("authorizationId")
                    if not auth_id:
                        auth_id = next(
                            (a["authorizationId"] for a in current_state.get("authorizations", {}).values() if a.get("requestId") == request_id),
                            None,
                        )
                    payment_info = None
                    if auth_id:
                        try:
                            from .routes_guard import execute_authorization
                            exec_res = await execute_authorization(auth_id, allow_idempotent=True)
                            payment_info = exec_res.get("payment")
                        except Exception:
                            pass

                    pub_url = (os.environ.get("GUARD_PUBLIC_URL") or "http://localhost:8002").rstrip("/")
                    checkout_url = f"{pub_url}/checkout/{auth_id}" if auth_id else None

                    return {
                        "requestId": request_id,
                        "decision": "APPROVED",
                        "status": payment_info.get("status", "AUTHORIZED").upper() if payment_info else "AUTHORIZED",
                        "riskScore": decision["riskScore"],
                        "policyVersion": decision["policyVersion"],
                        "authorizationId": auth_id,
                        "checkoutUrl": checkout_url,
                        "payment": payment_info,
                        "approvalRequired": False,
                        "message": f"User APPROVED payment on phone! Checkout link: {checkout_url}",
                    }
                elif resolution["action"] == "reject":
                    return {
                        "requestId": request_id,
                        "decision": "DENIED",
                        "status": "DENIED",
                        "riskScore": decision["riskScore"],
                        "approvalRequired": False,
                        "message": "User DECLINED payment on phone.",
                    }

    pub_url = (os.environ.get("GUARD_PUBLIC_URL") or "http://localhost:8002").rstrip("/")
    return {
        **decision,
        "status": "PENDING" if decision["decision"] == "USER_APPROVAL" else "ALLOWED",
        "approvalRequired": decision["decision"] == "USER_APPROVAL",
        "message": (
            f"Approval request {request_id} sent to user phone for {request['product']} (₹{request['amount']}). "
            f"Please tap ACCEPT in AgentPay Guard app. Call /agent/payment-status/{request_id} (or 'latest') to verify."
        ) if decision["decision"] == "USER_APPROVAL" else "Transaction auto-approved within policy limit.",
    }


@router.get("/payment-status/{request_id}")
async def payment_status(request_id: str, wait_seconds: int = 15) -> dict:
    """Poll an agent request: decision, user resolution, authorization, payment."""
    state = store.snapshot()
    
    if request_id.lower() in ("latest", "last", "recent", "current"):
        requests = list(state.get("requests", {}).values())
        if not requests:
            raise HTTPException(status_code=404, detail={"code": "NO_REQUESTS_FOUND", "message": "No payment requests found"})
        request = requests[-1]
        request_id = request["requestId"]
    else:
        request = state["requests"].get(request_id)
        if not request:
            matching = [r for r_id, r in state["requests"].items() if request_id.lower() in r_id.lower()]
            if matching:
                request = matching[-1]
                request_id = request["requestId"]
            else:
                recent_ids = list(state.get("requests", {}).keys())[-5:]
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "REQUEST_NOT_FOUND",
                        "message": f"Request '{request_id}' not found. Recent request IDs: {recent_ids}. Use 'latest' to check the most recent request.",
                        "recentRequestIds": recent_ids,
                    },
                )

    resolution = next(
        (r for r in state.get("resolutions", []) if r["requestId"] == request_id), None
    )
    decision = state["decisions"].get(request_id)

    if not resolution and decision and decision.get("decision") == "USER_APPROVAL" and wait_seconds > 0:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + min(wait_seconds, 25)
        while loop.time() < deadline:
            await asyncio.sleep(1.0)
            state = store.snapshot()
            resolution = next(
                (r for r in state.get("resolutions", []) if r["requestId"] == request_id), None
            )
            if resolution:
                break

    auth_id = decision.get("authorizationId") if decision else None
    if not auth_id:
        auth_id = next(
            (a["authorizationId"] for a in state.get("authorizations", {}).values() if a.get("requestId") == request_id),
            None,
        )

    payment = next(
        (
            p
            for p in state.get("payments", {}).values()
            if p.get("requestId") == request_id
        ),
        None,
    )

    if resolution and resolution.get("action") == "accept" and auth_id and not payment:
        try:
            from .routes_guard import execute_authorization
            exec_res = await execute_authorization(auth_id, allow_idempotent=True)
            payment = exec_res.get("payment")
            state = store.snapshot()
        except Exception:
            pass

    authorization = state["authorizations"].get(auth_id) if auth_id else None

    status_str = "PENDING"
    if decision and decision.get("decision") == "BLOCK":
        status_str = "BLOCKED"
    elif resolution and resolution.get("action") == "reject":
        status_str = "DENIED"
    elif payment:
        status_str = payment.get("status", "EXECUTED").upper()
    elif resolution and resolution.get("action") == "accept":
        status_str = "APPROVED"

    checkout_url = None
    if auth_id:
        pub_url = (os.environ.get("GUARD_PUBLIC_URL") or "http://localhost:8002").rstrip("/")
        checkout_url = f"{pub_url}/checkout/{auth_id}"

    return {
        "requestId": request_id,
        "status": status_str,
        "request": request,
        "decision": decision,
        "resolution": resolution,
        "authorization": authorization,
        "payment": payment,
        "checkoutUrl": checkout_url,
    }

