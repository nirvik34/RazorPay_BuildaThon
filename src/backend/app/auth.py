"""Owner authentication for the Guard dashboard.

Single-owner model (it's a personal guard device):
- First /auth/register claims the owner account; later registers are rejected.
- Login issues a 7-day session token.
- A long-lived device token (for the Android app) is shown once at register.
- Management endpoints require `Authorization: Bearer <token>`; the agent
  payment flow (payment-request, pending, approval action, checkout) stays
  token-free so Claude/MCP and the phone keep working.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from .state import LOCK, now_iso, store

SESSION_TTL_DAYS = 7


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()


def _new_salt() -> str:
    return os.urandom(16).hex()


def register_owner(name: str, email: str, password: str) -> dict[str, Any] | None:
    """Returns the created user, or None if an owner already exists."""
    with LOCK:
        state = store.state
        if state.get("users"):
            return None
        salt = _new_salt()
        user = {
            "name": name,
            "email": email.lower(),
            "salt": salt,
            "passwordHash": _hash_password(password, salt),
            "deviceToken": "dev_" + secrets.token_hex(20),
            "createdAt": now_iso(),
        }
        state.setdefault("users", {})[user["email"]] = user
        store.save()
        return user


def login(email: str, password: str) -> dict[str, Any] | None:
    """Returns {sessionToken, deviceToken, user} or None on bad credentials."""
    with LOCK:
        state = store.state
        user = state.get("users", {}).get(email.lower())
        if not user:
            return None
        if _hash_password(password, user["salt"]) != user["passwordHash"]:
            return None
        token = "sess_" + secrets.token_hex(24)
        state.setdefault("sessions", {})[token] = {
            "email": user["email"],
            "expiresAt": (
                datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
            ).isoformat(),
        }
        store.save()
        return {
            "sessionToken": token,
            "deviceToken": user["deviceToken"],
            "user": {"name": user["name"], "email": user["email"]},
        }


def authenticate_token(token: str | None) -> dict[str, Any] | None:
    """Session token OR device token → user dict, else None."""
    if not token:
        return None
    state = store.snapshot()
    session = state.get("sessions", {}).get(token)
    if session:
        if session["expiresAt"] < datetime.now(timezone.utc).isoformat():
            return None
        return state.get("users", {}).get(session["email"])
    if not token:
        return None
    for user in state.get("users", {}).values():
        if secrets.compare_digest(user.get("deviceToken", ""), token):
            return user
    return None


def authenticate_request_headers(auth_header: str | None) -> dict[str, Any] | None:
    """Accepts the raw Authorization header value ("Bearer <token>")."""
    token = (
        auth_header[7:].strip()
        if auth_header and auth_header.lower().startswith("bearer ")
        else auth_header
    )
    return authenticate_token(token)


def logout(token: str) -> bool:
    with LOCK:
        state = store.state
        if token in state.get("sessions", {}):
            del state["sessions"][token]
            store.save()
            return True
    return False


def owner_exists() -> bool:
    return bool(store.snapshot().get("users"))
