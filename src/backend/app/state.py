from __future__ import annotations

import copy
import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import settings

LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def default_state() -> dict:
    policy = {
        "policyId": "pol_default",
        "version": 3,
        "transactionLimit": 20000,
        "dailyLimit": 75000,
        "monthlyLimit": 200000,
        "allowedCategories": ["electronics", "groceries", "office_supplies"],
        "blockedCategories": ["gift_cards", "gambling", "cryptocurrency"],
        "blockedMerchants": [],
        "approvalRules": {
            "newMerchant": True,
            "international": True,
            "amountAbove": 10000,
            "highRisk": True,
        },
    }
    agents = {
        "claude-shopping-01": {
            "agentId": "claude-shopping-01",
            "name": "Claude Shopping Agent",
            "ownerId": "user_001",
            "status": "ACTIVE",
            "trustScore": 94,
            "riskState": "NORMAL",
            "policyId": "pol_default",
            "createdAt": now_iso(),
        },
        "gemini-shopping-02": {
            "agentId": "gemini-shopping-02",
            "name": "Gemini Shopping Agent",
            "ownerId": "user_001",
            "status": "ACTIVE",
            "trustScore": 81,
            "riskState": "NORMAL",
            "policyId": "pol_default",
            "createdAt": now_iso(),
        },
        "gpt-assistant-03": {
            "agentId": "gpt-assistant-03",
            "name": "ChatGPT Assistant",
            "ownerId": "user_001",
            "status": "ACTIVE",
            "trustScore": 88,
            "riskState": "NORMAL",
            "policyId": "pol_default",
            "createdAt": now_iso(),
        },
    }
    intents = {
        "intent_183": {
            "intentId": "intent_183",
            "agentId": "claude-shopping-01",
            "goal": "Find me noise-cancelling headphones under ₹15,000.",
            "category": "electronics",
            "budget": 15000,
            "currency": "INR",
            "createdAt": now_iso(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
    }
    return {
        "users": {},
        "sessions": {},
        "agents": agents,
        "policies": {"pol_default": policy},
        "intents": intents,
        "requests": {},
        "decisions": {},
        "authorizations": {},
        "audit": {},
        "anomalies": [],
    }


class StateStore:
    def __init__(self) -> None:
        self._state = default_state()
        self.load()

    @property
    def state(self) -> dict:
        with LOCK:
            return self._state

    def load(self) -> None:
        path = Path(settings.data_file)
        if path.exists():
            try:
                self._state = json.loads(path.read_text())
            except json.JSONDecodeError:
                self._state = default_state()

    def save(self) -> None:
        path = Path(settings.data_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._state, indent=2))

    def reset(self) -> None:
        with LOCK:
            self._state = default_state()
            self.save()

    def snapshot(self) -> dict:
        with LOCK:
            return copy.deepcopy(self._state)


store = StateStore()
