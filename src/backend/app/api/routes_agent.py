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


@router.post("/payment-request")
async def payment_request(
    payload: PaymentRequestIn,
    x_agent_key: str | None = Header(default=None),
) -> dict:
    snapshot = store.snapshot()
    agent_id = payload.agentId

    if agent_id not in snapshot["agents"]:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AGENT_UNKNOWN",
                "message": f"Agent {agent_id} is not registered",
            },
        )

    request_id = payload.requestId or f"req_{uuid.uuid4().hex[:6]}"
    request = {
        "requestId": request_id,
        "agentId": agent_id,
        "intentId": payload.intentId,
        "merchant": payload.merchant.lower(),
        "product": payload.product,
        "amount": payload.amount,
        "currency": payload.currency,
        "category": payload.category,
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

    return {
        **decision,
        "approvalRequired": decision["decision"] == "USER_APPROVAL",
    }
