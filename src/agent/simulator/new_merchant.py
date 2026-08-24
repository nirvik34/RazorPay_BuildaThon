from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import OTHER_AGENT, banner, report  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base, agent_id=OTHER_AGENT)
    banner("SCENE — NEW MERCHANT REQUIRES APPROVAL")

    pr, decision = agent.checkout(
        "Monthly groceries basket",
        "bigbasket",
        6400,
        "groceries",
        session_id="sess_newmerchant_demo",
    )
    report("Payment request evaluated", pr, decision)
    if decision.decision == "USER_APPROVAL":
        act = agent.client.approve(pr.requestId or "")
        auth_id = act["authorization"]["authorizationId"]
        pay = agent.client.execute_payment(auth_id)
        print(
            f"    user ACCEPTED new merchant → {auth_id} → {pay['payment']['status']}"
        )


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
