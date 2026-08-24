from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import OTHER_AGENT, banner, report  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base, agent_id=OTHER_AGENT)
    banner("SCENE 2 — OVER-LIMIT PURCHASE")
    print("Policy limit: ₹20,000 per transaction. Agent tries a ₹42,000 MacBook.")

    pr, decision = agent.checkout(
        "MacBook Pro 14",
        "techmart",
        42000,
        "electronics",
        session_id="sess_overlimit_demo",
    )
    report("Payment request evaluated", pr, decision)
    assert (
        decision.decision == "BLOCK"
        and decision.block_reason == "LIMIT_TRANSACTION_EXCEEDED"
    )
    print("    no approval was requested — hard policy blocked it locally.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
