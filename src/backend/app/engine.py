from __future__ import annotations

from datetime import datetime
from typing import Any

VELOCITY_WINDOW_S = 600
CIRCUMVENTION_WINDOW_S = 300


def _parse(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


def _same_day(a: str, b: str) -> bool:
    return datetime.fromisoformat(a).date() == datetime.fromisoformat(b).date()


def known_merchants(history: list[dict]) -> set[str]:
    known = set()
    for rec in history:
        decision_type = rec["decision"]["decision"]
        approved = decision_type == "ALLOW" or (
            decision_type == "USER_APPROVAL" and rec.get("outcome") == "CAPTURED"
        )
        if approved:
            known.add(rec["request"]["merchant"])
    return known


def today_approved_spend(history: list[dict], agent_id: str, now_ts: str) -> int:
    total = 0
    for rec in history:
        req = rec["request"]
        if req["agentId"] != agent_id:
            continue
        if rec["decision"]["decision"] == "BLOCK":
            continue
        if rec.get("outcome") != "CAPTURED":
            continue
        if _parse(req["timestamp"]) > _parse(now_ts):
            continue
        total += req["amount"]
    return total


def score_intent(request: dict, intents: dict[str, dict]) -> tuple[int, bool, bool]:
    intent_id = request.get("intentId")
    if not intent_id or intent_id not in intents:
        return 50, False, False
    intent = intents[intent_id]
    if request["category"] != intent["category"]:
        return 15, True, True
    amount = request["amount"]
    budget = intent["budget"]
    if amount > budget * 1.5:
        return 15, True, True
    if amount > budget * 1.1:
        return 55, False, True
    return min(100, 90 + int((budget - amount) / max(budget, 1) * 20)), False, False


def compute_risk(
    request: dict, policy: dict, history: list[dict], known: set[str], now: str
) -> tuple[int, str, list[str]]:
    signals: list[str] = []
    score = 0

    if request["merchant"] not in known:
        score += 22
        signals.append("Merchant not previously approved")

    amount_factor = min(20, round(request["amount"] / policy["transactionLimit"] * 20))
    score += amount_factor
    if amount_factor >= 10:
        signals.append("Amount close to transaction limit")

    hour = datetime.fromisoformat(request["timestamp"]).hour
    if hour < 8 or hour >= 21:
        score += 12
        signals.append("Unusual spending time")

    ts = _parse(request["timestamp"])
    recent = [
        rec
        for rec in history
        if rec["request"]["agentId"] == request["agentId"]
        and 0 <= ts - _parse(rec["request"]["timestamp"]) <= VELOCITY_WINDOW_S
    ]
    if len(recent) + 1 >= 3:
        score += 15
        signals.append(f"High velocity: {len(recent) + 1} requests in 10 minutes")

    used = {
        rec["request"]["category"]
        for rec in history
        if rec["request"]["agentId"] == request["agentId"]
    }
    if request["category"] not in used:
        score += 12
        signals.append(f"Unfamiliar category for this agent: {request['category']}")

    blocked_today = any(
        rec["request"]["agentId"] == request["agentId"]
        and rec["decision"]["decision"] == "BLOCK"
        and _same_day(rec["request"]["timestamp"], now)
        for rec in history
    )
    if blocked_today:
        score += 14
        signals.append("Agent had a blocked action today")

    score = max(0, min(100, score))
    level = (
        "LOW"
        if score < 25
        else "MEDIUM"
        if score < 50
        else "HIGH"
        if score < 75
        else "CRITICAL"
    )
    if not signals:
        signals.append("Activity within baseline")
    return score, level, signals


def detect_circumvention(
    request: dict, policy: dict, history: list[dict]
) -> dict[str, Any]:
    ts = _parse(request["timestamp"])
    prior: list[dict] = []

    for rec in history:
        if rec["decision"]["decision"] == "BLOCK":
            continue
        req = rec["request"]
        if (
            req["agentId"] != request["agentId"]
            or req["sessionId"] != request["sessionId"]
        ):
            continue
        t = _parse(req["timestamp"])
        if t > ts or ts - t > CIRCUMVENTION_WINDOW_S:
            continue
        ratio = (
            abs(req["amount"] - request["amount"]) / req["amount"]
            if req["amount"]
            else 1.0
        )
        same_context = (
            req["merchant"] == request["merchant"]
            and req["category"] == request["category"]
        )
        if ratio <= 0.15 or same_context:
            prior.append(rec)

    aggregate = sum(rec["request"]["amount"] for rec in prior) + request["amount"]
    if len(prior) >= 2 and aggregate >= 0.9 * policy["transactionLimit"]:
        return {
            "detected": True,
            "score": min(100, 55 + 15 * len(prior)),
            "aggregateAmount": aggregate,
            "windowCount": len(prior) + 1,
        }
    score = min(60, len(prior) * 20) if prior else 0
    return {
        "detected": False,
        "score": score,
        "aggregateAmount": aggregate,
        "windowCount": len(prior) + 1,
    }


def evaluate_request(
    request: dict,
    agent: dict,
    policy: dict,
    history: list[dict],
    intents: dict[str, dict],
    now: str | None = None,
) -> dict:
    now = now or request["timestamp"]
    known = known_merchants(history)
    risk_score, risk_level, risk_signals = compute_risk(
        request, policy, history, known, now
    )
    circ = detect_circumvention(request, policy, history)
    intent_score, severe, warn_budget = score_intent(request, intents)

    reasons: list[dict] = []
    if agent["status"] == "ACTIVE":
        reasons.append(
            {"code": "AGENT_AUTHORIZED", "label": "Agent authorized", "severity": "ok"}
        )
    if request["category"] in policy["blockedCategories"]:
        reasons.append(
            {
                "code": "CATEGORY_BLOCKED",
                "label": f"Category {request['category']} is disabled",
                "severity": "block",
            }
        )
    else:
        reasons.append(
            {
                "code": "CATEGORY_ALLOWED",
                "label": f"Category {request['category']} allowed",
                "severity": "ok",
            }
        )
    if request["merchant"] in policy["blockedMerchants"]:
        reasons.append(
            {
                "code": "MERCHANT_BLOCKED",
                "label": f"Merchant {request['merchant']} is prohibited",
                "severity": "block",
            }
        )
    elif request["merchant"] in known:
        reasons.append(
            {"code": "MERCHANT_KNOWN", "label": "Known merchant", "severity": "ok"}
        )
    else:
        reasons.append(
            {
                "code": "NEW_MERCHANT",
                "label": "New merchant requires review",
                "severity": "warn",
            }
        )

    spend = today_approved_spend(history, request["agentId"], now)
    daily_exceeded = spend + request["amount"] > policy["dailyLimit"]

    decision = "ALLOW"

    def hard(code: str, label: str):
        reasons.append({"code": code, "label": label, "severity": "block"})

    checks = {
        "revoked": agent["status"] == "REVOKED",
        "frozen": agent["status"] == "FROZEN",
        "category_blocked": any(r["code"] == "CATEGORY_BLOCKED" for r in reasons),
        "merchant_blocked": any(r["code"] == "MERCHANT_BLOCKED" for r in reasons),
        "limit_txn": request["amount"] > policy["transactionLimit"],
        "limit_daily": daily_exceeded,
        "intent_severe": severe,
        "circumvention": circ["detected"],
    }

    if checks["revoked"]:
        hard("AGENT_REVOKED", "Agent access has been revoked")
        decision = "BLOCK"
    elif checks["frozen"]:
        hard("AGENT_FROZEN", "Agent is frozen on this device")
        decision = "BLOCK"
    elif checks["category_blocked"]:
        decision = "BLOCK"
    elif checks["merchant_blocked"]:
        decision = "BLOCK"
    elif checks["limit_txn"]:
        hard(
            "LIMIT_TRANSACTION_EXCEEDED",
            f"\u20b9{request['amount']} exceeds \u20b9{policy['transactionLimit']} transaction limit (send amount in INR Rupees, not paise)",
        )
        decision = "BLOCK"
    elif checks["limit_daily"]:
        hard(
            "LIMIT_DAILY_EXCEEDED",
            f"Daily exposure would exceed \u20b9{policy['dailyLimit']}",
        )
        decision = "BLOCK"
    elif checks["intent_severe"]:
        hard("INTENT_MISMATCH", "Transaction does not match user intent")
        decision = "BLOCK"
    elif checks["circumvention"]:
        hard(
            "CIRCUMVENTION_DETECTED",
            f"Split pattern: {circ['windowCount']} payments, aggregate \u20b9{circ['aggregateAmount']}",
        )
        decision = "BLOCK"
    elif request["amount"] > policy["transactionLimit"]:
        pass

    if (
        decision == "ALLOW"
        and request["amount"] <= policy["transactionLimit"]
        and not severe
    ):
        if not warn_budget:
            reasons.append(
                {
                    "code": "BUDGET_VALID",
                    "label": "Budget within intent",
                    "severity": "ok",
                }
            )
        else:
            reasons.append(
                {
                    "code": "BUDGET_WARN",
                    "label": "Amount exceeds intent budget",
                    "severity": "warn",
                }
            )
    if decision == "ALLOW" and request["amount"] <= policy["transactionLimit"]:
        reasons.append(
            {
                "code": "LIMIT_WITHIN",
                "label": "Within transaction limit",
                "severity": "ok",
            }
        )

    rules = policy["approvalRules"]
    if decision == "ALLOW":
        if request["merchant"] not in known and rules["newMerchant"]:
            decision = "USER_APPROVAL"
        elif request["amount"] >= rules["amountAbove"]:
            reasons.append(
                {
                    "code": "AMOUNT_REQUIRES_APPROVAL",
                    "label": f"Amount at or above \u20b9{rules['amountAbove']} approval threshold",
                    "severity": "warn",
                }
            )
            decision = "USER_APPROVAL"
        elif (risk_level in ("HIGH", "CRITICAL")) and rules["highRisk"]:
            reasons.append(
                {"code": "HIGH_RISK", "label": f"Risk {risk_level}", "severity": "warn"}
            )
            decision = "USER_APPROVAL"
        else:
            reasons.append(
                {
                    "code": "POLICY_PASSED",
                    "label": "Policy checks passed",
                    "severity": "ok",
                }
            )

    return {
        "requestId": request["requestId"],
        "decision": decision,
        "reasonCodes": reasons,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "riskSignals": risk_signals,
        "intentScore": intent_score,
        "circumventionScore": circ["score"],
        "circumvention": circ,
        "policyVersion": policy["version"],
        "authorizationId": None,
        "timestamp": now,
    }
