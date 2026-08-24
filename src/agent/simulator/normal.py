from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.base import AGENT_ID, banner, report  # noqa: E402
from tools.catalog import compare_products, search_catalog, select_product  # noqa: E402


def run(api_base: str) -> None:
    from simulator.base import ShoppingAgentSimulator

    agent = ShoppingAgentSimulator(api_base)
    banner("SCENE 1 — LEGITIMATE PURCHASE")
    print('User intent: "Find me noise-cancelling headphones under ₹15,000."')

    results = compare_products(search_catalog("sony"))
    chosen = select_product([r for r in results if r.price <= 15000])
    print(f"Agent selected: {chosen.product} @ {chosen.merchant} — ₹{chosen.price:,}")

    intent_id = agent.client.create_intent(
        goal="Find me noise-cancelling headphones under ₹15,000.",
        category="electronics",
        budget=15000,
    )

    pr, decision = agent.checkout(
        chosen.product,
        chosen.merchant,
        chosen.price,
        chosen.category,
        intent_id=intent_id,
    )
    t0 = time.perf_counter()
    report("Payment request evaluated", pr, decision)
    print(f"    guard latency: {(time.perf_counter() - t0) * 1000:.1f}ms")

    if decision.decision == "USER_APPROVAL":
        act = agent.client.approve(pr.requestId or "")
        auth_id = act["authorization"]["authorizationId"]
        print(f"    user ACCEPTED → authorization {auth_id}")
        pay = agent.client.execute_payment(auth_id)
        print(f"    razorpay: {pay['payment']['id']} status={pay['payment']['status']}")
        replay = f'curl -X POST {api_base}/guard/payments/execute -d \'{{"authorizationId": "{auth_id}"}}\''
        print(f"    (replay of the same auth is rejected — single use)")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
