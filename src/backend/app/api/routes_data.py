from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..state import LOCK, store

router = APIRouter(tags=["data"])


@router.get("/agents")
async def agents() -> dict:
    return {"agents": list(store.snapshot()["agents"].values())}


@router.get("/policies")
async def policies() -> dict:
    return {"policies": list(store.snapshot()["policies"].values())}


class PolicyUpdate(BaseModel):
    transactionLimit: Optional[int] = None
    dailyLimit: Optional[int] = None
    monthlyLimit: Optional[int] = None
    blockedCategories: Optional[list[str]] = None
    blockedMerchants: Optional[list[str]] = None
    amountAbove: Optional[int] = None
    newMerchant: Optional[bool] = None
    highRisk: Optional[bool] = None


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate) -> dict:
    with LOCK:
        state = store.state
        policy = state["policies"].get(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail={"code": "POLICY_NOT_FOUND"})
        for field_name in ("transactionLimit", "dailyLimit", "monthlyLimit"):
            value = getattr(payload, field_name)
            if value is not None:
                policy[field_name] = value
        if payload.blockedCategories is not None:
            policy["blockedCategories"] = payload.blockedCategories
        if payload.blockedMerchants is not None:
            policy["blockedMerchants"] = payload.blockedMerchants
        rules = policy["approvalRules"]
        if payload.amountAbove is not None:
            rules["amountAbove"] = payload.amountAbove
        if payload.newMerchant is not None:
            rules["newMerchant"] = payload.newMerchant
        if payload.highRisk is not None:
            rules["highRisk"] = payload.highRisk
        policy["version"] += 1
        store.save()
    return {"ok": True, "policy": policy}


class SyncAuditIn(BaseModel):
    events: list[dict]


@router.post("/sync/audit")
async def sync_audit(payload: SyncAuditIn) -> dict:
    accepted = 0
    with LOCK:
        state = store.state
        for event in payload.events:
            request_id = event.get("requestId")
            if not request_id:
                continue
            state["audit"].setdefault(request_id, [])
            known_ids = {e.get("eventId") for e in state["audit"][request_id]}
            if event.get("eventId") not in known_ids:
                state["audit"][request_id].append(event)
                accepted += 1
        store.save()
    return {"ok": True, "accepted": accepted}


def _txn_view(state: dict) -> list[dict]:
    out = []
    for request_id, decision in state["decisions"].items():
        req = state["requests"].get(request_id)
        if not req:
            continue
        resolution = next(
            (r for r in state.get("resolutions", []) if r["requestId"] == request_id),
            None,
        )
        auth_id = decision.get("authorizationId")
        auth = state["authorizations"].get(auth_id) if auth_id else None
        payment = next(
            (
                p
                for p in state.get("payments", {}).values()
                if p.get("requestId") == request_id
            ),
            None,
        )
        outcome = "NOT_ATTEMPTED"
        if decision["decision"] == "BLOCK":
            outcome = "NOT_ATTEMPTED"
        elif payment and payment.get("status") == "captured":
            outcome = "CAPTURED"
        elif resolution and resolution["action"] == "reject":
            outcome = "DENIED"
        elif auth or decision["decision"] == "ALLOW":
            outcome = (
                "CAPTURED"
                if (payment and payment.get("status") == "captured")
                else "PROCESSING"
            )
        out.append(
            {
                "request": req,
                "decision": decision,
                "outcome": outcome,
                "authorization": auth,
            }
        )
    return sorted(out, key=lambda r: r["request"]["timestamp"], reverse=True)


@router.get("/transactions")
async def transactions() -> dict:
    return {"transactions": _txn_view(store.snapshot())}


@router.get("/audit/{request_id}")
async def audit_detail(request_id: str) -> dict:
    state = store.snapshot()
    if request_id not in state["requests"]:
        raise HTTPException(status_code=404, detail={"code": "REQUEST_NOT_FOUND"})
    return {
        "request": state["requests"][request_id],
        "decision": state["decisions"].get(request_id),
        "audit": state["audit"].get(request_id, []),
    }
