from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..engine import evaluate_request
from ..state import now_iso, store

router = APIRouter(prefix="/simulate", tags=["simulation"])

KNOWN = ["amazon", "flipkart", "bigbasket", "croma"]
UNKNOWN = ["shopquick", "gadgethub", "megamart", "valuecart", "techdeals"]
ALLOWED = ["electronics", "groceries", "office_supplies"]
PRODUCTS: dict[str, list[str]] = {
    "electronics": [
        "Wireless earbuds",
        "USB-C cable",
        "Bluetooth speaker",
        "Power bank",
    ],
    "groceries": ["Atta 5kg", "Rice 10kg", "Cooking oil 1L"],
    "office_supplies": ["Notebook set", "Desk organizer"],
    "gift_cards": ["Amazon Pay Gift Card"],
}


class SimulateIn(BaseModel):
    count: int = Field(default=10000, ge=1, le=100000)
    seed: int = 42


@router.post("")
async def simulate(payload: SimulateIn) -> dict[str, Any]:
    rng = random.Random(payload.seed)
    state = store.snapshot()
    policy = next(iter(state["policies"].values()))
    agents = state["agents"]

    history: list[dict] = []
    allowed = approval_required = blocked = prevented = 0
    by_reason: dict[str, int] = {}

    per_day = 8

    def stamp_for(index: int) -> str:
        from datetime import datetime, timedelta

        day_back = index // per_day
        base = datetime.now().replace(
            hour=9 + (index * 7) % 12,
            minute=(index * 13) % 60,
            second=(index * 29) % 60,
        )
        return (base - timedelta(days=day_back)).isoformat(timespec="seconds")

    n = 0
    while n < payload.count:
        roll = rng.random()
        batch: list[dict] = []
        base_ts = stamp_for(n)

        def mk(
            merchant: str, category: str, product: str, amount: int, session: str
        ) -> dict:
            return {
                "requestId": f"sim_{n + len(batch) + 1:05d}",
                "agentId": "claude-shopping-01",
                "intentId": None,
                "merchant": merchant,
                "product": product,
                "amount": amount,
                "currency": "INR",
                "category": category,
                "sessionId": session,
                "timestamp": base_ts,
            }

        if roll < 0.62:
            cat = ALLOWED[rng.randrange(len(ALLOWED))]
            batch.append(
                mk(
                    KNOWN[rng.randrange(len(KNOWN))],
                    cat,
                    PRODUCTS[cat][rng.randrange(len(PRODUCTS[cat]))],
                    150 + rng.randrange(8500),
                    f"s_{n}",
                )
            )
        elif roll < 0.74:
            batch.append(
                mk(
                    KNOWN[rng.randrange(len(KNOWN))],
                    "electronics",
                    "MacBook Pro 14",
                    12000 + rng.randrange(48000),
                    f"s_{n}",
                )
            )
        elif roll < 0.82:
            batch.append(
                mk(
                    KNOWN[rng.randrange(len(KNOWN))],
                    "gift_cards",
                    PRODUCTS["gift_cards"][0],
                    2000 + rng.randrange(8000),
                    f"s_{n}",
                )
            )
        elif roll < 0.92:
            batch.append(
                mk(
                    UNKNOWN[rng.randrange(len(UNKNOWN))],
                    ALLOWED[rng.randrange(len(ALLOWED))],
                    "Assorted order",
                    800 + rng.randrange(7000),
                    f"s_{n}",
                )
            )
        elif roll < 0.97:
            merchant = UNKNOWN[rng.randrange(len(UNKNOWN))]
            for k in range(3):
                batch.append(
                    mk(
                        merchant,
                        "electronics",
                        "Bundle item",
                        9400 + rng.randrange(500),
                        f"split_{n}",
                    )
                )
        else:
            merchant = UNKNOWN[rng.randrange(len(UNKNOWN))]
            for k in range(6):
                batch.append(
                    mk(
                        merchant,
                        "electronics",
                        "Flash sale item",
                        3000 + rng.randrange(6500),
                        f"burst_{n}",
                    )
                )

        agent = agents.get("claude-shopping-01")
        if not agent:
            continue

        for req in batch:
            if n >= payload.count:
                break
            n += 1
            decision = evaluate_request(req, agent, policy, history, state["intents"])
            row: dict = {"request": req, "decision": decision}
            if decision["decision"] == "USER_APPROVAL" and rng.random() < 0.8:
                row["outcome"] = "CAPTURED"
            elif decision["decision"] == "ALLOW":
                row["outcome"] = "CAPTURED"
            history.append(row)

            if decision["decision"] == "BLOCK":
                blocked += 1
                prevented += req["amount"]
                code = next(
                    (
                        r["code"]
                        for r in decision["reasonCodes"]
                        if r["severity"] == "block"
                    ),
                    "BLOCKED",
                )
                by_reason[code] = by_reason.get(code, 0) + 1
            elif decision["decision"] == "USER_APPROVAL":
                approval_required += 1
                code = next(
                    (
                        r["code"]
                        for r in decision["reasonCodes"]
                        if r["severity"] == "warn"
                    ),
                    "APPROVAL",
                )
                by_reason[code] = by_reason.get(code, 0) + 1
            else:
                allowed += 1
                by_reason["AUTO_APPROVED"] = by_reason.get("AUTO_APPROVED", 0) + 1

    stages = {
        "received": payload.count,
        "authority": by_reason.get("AGENT_FROZEN", 0)
        + by_reason.get("AGENT_REVOKED", 0),
        "policy": by_reason.get("CATEGORY_BLOCKED", 0)
        + by_reason.get("LIMIT_TRANSACTION_EXCEEDED", 0)
        + by_reason.get("LIMIT_DAILY_EXCEEDED", 0),
        "risk": by_reason.get("CIRCUMVENTION_DETECTED", 0)
        + by_reason.get("INTENT_MISMATCH", 0),
        "decided": payload.count,
    }

    return {
        "requests": payload.count,
        "allowed": allowed,
        "approvalRequired": approval_required,
        "blocked": blocked,
        "byReason": by_reason,
        "preventedAmount": prevented,
        "stages": stages,
    }
