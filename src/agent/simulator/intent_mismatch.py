from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import AGENT_ID, banner, report  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base, agent_id=AGENT_ID)
    banner("SCENE 4 — INTENT MANIPULATION")
    print('User intent: "Buy me a monitor under ₹20,000."')
    intent_id = agent.client.create_intent(
        goal="Buy me a monitor under ₹20,000.", category="electronics", budget=20000
    )
    print("Agent instead attempts: Amazon Pay Gift Card ₹10,000")

    pr, decision = agent.checkout(
        "Amazon Pay Gift Card ₹10,000",
        "flipkart",
        10000,
        "gift_cards",
        intent_id=intent_id,
        session_id="sess_intent_demo",
    )
    report("Payment request evaluated", pr, decision)
    assert decision.decision == "BLOCK"
    print("    blocked before any user prompt — category disabled AND intent mismatch.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
