from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import AGENT_ID, banner, report  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base, agent_id=AGENT_ID)
    banner("SCENE 3 — TRANSACTION SPLITTING (CIRCUMVENTION)")
    session = f"sess_split_{uuid.uuid4().hex[:6]}"
    print("Each item is under the ₹20,000 transaction limit:")
    items = [
        ("Logitech MX Master 3S", "croma", 9800),
        ("Keychron K3 Keyboard", "croma", 9700),
        ("Anker USB-C Hub", "croma", 9900),
    ]
    for product, merchant, amount in items:
        pr, decision = agent.checkout(
            product, merchant, amount, "electronics", session_id=session
        )
        report("Payment request evaluated", pr, decision)

    print("\n    The Guard correlated the sequence: same agent · same session")
    print("    similar amounts · short window → aggregate ₹29,400 vs ₹20,000 limit.")
    print("    Third request blocked as CIRCUMVENTION_DETECTED.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
