"""End-to-end smoke test: agent request → approval → scoped authorization → payment."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.state import store  # noqa: E402


def main() -> None:
    store.reset()
    with TestClient(app) as client:
        health = client.get("/health").json()
        print("health:", health)
        assert health["status"] == "ok"

        payload = {
            "agentId": "claude-shopping-01",
            "intentId": "intent_183",
            "merchant": "amazon",
            "product": "Sony WH-1000XM5",
            "amount": 14499,
            "category": "electronics",
        }
        r1 = client.post("/agent/payment-request", json=payload).json()
        print("headphones:", r1["decision"], [rc["code"] for rc in r1["reasonCodes"]])
        assert r1["decision"] == "USER_APPROVAL"

        req_id = client.get("/guard/pending").json()[0]["request"]["requestId"]
        act = client.post(
            f"/guard/approvals/{req_id}/action", json={"action": "accept"}
        ).json()
        auth_id = act["authorization"]["authorizationId"]
        print("authorization:", auth_id)

        pay = client.post(
            "/guard/payments/execute", json={"authorizationId": auth_id}
        ).json()
        print("payment:", pay["payment"]["id"], pay["payment"]["status"])
        assert pay["payment"]["status"] == "captured"
        replay = client.post(
            "/guard/payments/execute", json={"authorizationId": auth_id}
        )
        assert replay.status_code == 409, "scoped authorization must be single-use"
        print("replay blocked:", replay.json()["detail"]["code"])

        over = client.post(
            "/agent/payment-request",
            json={
                "agentId": "gemini-shopping-02",
                "merchant": "techmart",
                "product": "MacBook Pro 14",
                "amount": 42000,
                "category": "electronics",
            },
        ).json()
        print("over-limit:", over["decision"])
        assert over["decision"] == "BLOCK" and any(
            rc["code"] == "LIMIT_TRANSACTION_EXCEEDED" for rc in over["reasonCodes"]
        )

        split_session = "sess_smoke_split"
        decisions = []
        for amount in (9800, 9700, 9900):
            d = client.post(
                "/agent/payment-request",
                json={
                    "agentId": "claude-shopping-01",
                    "merchant": "croma",
                    "product": f"Accessory {amount}",
                    "amount": amount,
                    "category": "electronics",
                    "sessionId": split_session,
                },
            ).json()
            decisions.append(d["decision"])
        print("splitting sequence:", decisions)
        assert decisions == ["USER_APPROVAL", "USER_APPROVAL", "BLOCK"]

        gift = client.post(
            "/agent/payment-request",
            json={
                "agentId": "gpt-assistant-03",
                "merchant": "flipkart",
                "product": "Gift card",
                "amount": 5000,
                "category": "gift_cards",
            },
        ).json()
        assert gift["decision"] == "BLOCK" and any(
            rc["code"] == "CATEGORY_BLOCKED" for rc in gift["reasonCodes"]
        )
        print("gift card:", gift["decision"])

        sim = client.post("/simulate", json={"count": 2000, "seed": 7}).json()
        print(
            "simulation:",
            f"allowed={sim['allowed']} approval={sim['approvalRequired']} blocked={sim['blocked']}",
            f"prevented=₹{sim['preventedAmount']}",
        )
        assert sim["requests"] == 2000 and sim["blocked"] > 0

        audit = client.get(f"/audit/{req_id}").json()
        labels = [e["label"] for e in audit["audit"]]
        assert "Authorization issued" in labels and "Payment captured" in labels
        print("audit chain ok:", len(labels), "events")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
