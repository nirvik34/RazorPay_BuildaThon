from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

CATEGORIES = [
    "electronics",
    "groceries",
    "office_supplies",
    "gift_cards",
    "gambling",
    "cryptocurrency",
    "fashion",
    "travel",
]


@dataclass
class PaymentRequest:
    agentId: str
    merchant: str
    product: str
    amount: int
    category: str
    intentId: str | None = None
    sessionId: str | None = None
    requestId: str | None = None


@dataclass
class GuardDecision:
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def decision(self) -> str:
        return self.raw.get("decision", "?")

    @property
    def reason_codes(self) -> list[str]:
        return [rc.get("code", "") for rc in self.raw.get("reasonCodes", [])]

    @property
    def block_reason(self) -> str | None:
        for rc in self.raw.get("reasonCodes", []):
            if rc.get("severity") == "block":
                return rc.get("code")
        return None


class GuardClient:
    def __init__(self, api_base: str, agent_key: str | None = None) -> None:
        self.api_base = api_base.rstrip("/")
        self.agent_key = agent_key

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()
            raise RuntimeError(
                f"POST {path} failed: {exc.code} {detail[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach AgentPay Guard at {self.api_base}. Start the backend first:\n"
                f"  cd src/backend && uvicorn app.main:app --reload"
            ) from exc

    def create_intent(self, goal: str, category: str, budget: int) -> str:
        result = self._post(
            f"/agent/intent?agentId=claude-shopping-01",
            {"goal": goal, "category": category, "budget": budget},
        )
        return result["intentId"]

    def request_payment(self, pr: PaymentRequest) -> GuardDecision:
        body: dict[str, Any] = {
            "agentId": pr.agentId,
            "merchant": pr.merchant,
            "product": pr.product,
            "amount": pr.amount,
            "currency": "INR",
            "category": pr.category,
        }
        if pr.intentId:
            body["intentId"] = pr.intentId
        if pr.sessionId:
            body["sessionId"] = pr.sessionId
        if pr.requestId:
            body["requestId"] = pr.requestId
        headers = {"X-Agent-Key": self.agent_key or pr.agentId}
        req = urllib.request.Request(
            f"{self.api_base}/agent/payment-request?wait_seconds=0",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return GuardDecision(json.loads(resp.read().decode()))

    def approve(self, request_id_hint: str) -> dict[str, Any]:
        import urllib.request as u

        with u.urlopen(f"{self.api_base}/guard/pending", timeout=15) as resp:
            pending = json.loads(resp.read().decode())
        target = next(
            (
                p
                for p in pending
                if p["request"]["requestId"].startswith(request_id_hint)
            ),
            pending[0],
        )
        rid = target["request"]["requestId"]
        body = json.dumps({"action": "accept"}).encode()
        req = u.Request(
            f"{self.api_base}/guard/approvals/{rid}/action",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with u.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def execute_payment(self, authorization_id: str) -> dict[str, Any]:
        import urllib.request as u

        body = json.dumps({"authorizationId": authorization_id}).encode()
        req = u.Request(
            f"{self.api_base}/guard/payments/execute",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with u.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def freeze_agent(self, agent_id: str) -> dict[str, Any]:
        import urllib.request as u

        req = u.Request(
            f"{self.api_base}/guard/agents/{agent_id}/freeze",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with u.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
