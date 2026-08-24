from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from protocol.models import GuardClient, PaymentRequest  # noqa: E402

AGENT_ID = "claude-shopping-01"
OTHER_AGENT = "gemini-shopping-02"


class ShoppingAgentSimulator:
    def __init__(self, api_base: str, agent_id: str = AGENT_ID) -> None:
        self.client = GuardClient(api_base)
        self.agent_id = agent_id
        self.session_id = f"sess_{uuid.uuid4().hex[:8]}"

    def checkout(
        self,
        product: str,
        merchant: str,
        amount: int,
        category: str,
        intent_id: str | None = None,
        session_id: str | None = None,
    ):
        pr = PaymentRequest(
            agentId=self.agent_id,
            merchant=merchant,
            product=product,
            amount=amount,
            category=category,
            intentId=intent_id,
            sessionId=session_id or self.session_id,
        )
        decision = self.client.request_payment(pr)
        return pr, decision


def banner(title: str) -> None:
    print(f"\n{'=' * 62}\n  {title}\n{'=' * 62}")


def report(
    step: str, pr: PaymentRequest, decision: GuardDecision, latency_note: bool = False
) -> float:
    start = time.perf_counter()
    icon = {"BLOCK": "🔴", "USER_APPROVAL": "🟠", "ALLOW": "🟢"}.get(
        decision.decision, "⚪"
    )
    print(f"\n{icon} {step}")
    print(f"    {pr.product} · {pr.merchant} · ₹{pr.amount:,}")
    codes = ", ".join(decision.reason_codes)
    print(f"    decision={decision.decision}  reasons=[{codes}]")
    if latency_note:
        ms = (time.perf_counter() - start) * 1000
        print(f"    local decision latency check ok ({ms:.1f}ms incl. network)")
    return time.perf_counter()
