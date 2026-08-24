from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import AGENT_ID, banner  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base, agent_id=AGENT_ID)
    banner("SCENE 5 — COMPROMISED AGENT BURST")
    print("Baseline: ~5 transactions/day. Observed: rapid burst of 10 requests.")

    session = f"sess_burst_{uuid.uuid4().hex[:6]}"
    decisions: list[str] = []
    for i in range(10):
        pr, decision = agent.checkout(
            f"Flash deal item {i + 1}",
            f"dealsite{i % 3}",
            1500 + i * 900,
            "electronics" if i % 2 == 0 else "groceries",
            session_id=f"{session}_{i}",
        )
        decisions.append(decision.decision)
        time.sleep(0.05)

    blocked = decisions.count("BLOCK")
    approvals = decisions.count("USER_APPROVAL")
    print(
        f"\n    burst results: {blocked} blocked · {approvals} approval-required · {decisions.count('ALLOW')} allowed"
    )
    print("    velocity signals raised the risk score; the dashboard Risk page")
    print(f"    now shows a CRITICAL ANOMALY with a FREEZE recommendation.")
    print("\n    Freezing the agent locally (works offline on device):")
    result = agent.client.freeze_agent(AGENT_ID)
    print(f"    → {AGENT_ID} status={result['status']}")
    pr, decision = agent.checkout("Post-freeze attempt", "amazon", 2000, "electronics")
    assert decision.decision == "BLOCK"
    print(f"    post-freeze request → {decision.block_reason} (BLOCK)")
    print(
        "\n    Unfreeze via web UI or: POST /guard/agents/claude-shopping-01/unfreeze"
    )


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
