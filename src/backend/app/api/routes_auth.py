from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .. import auth
from ..state import store

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


@router.get("/status")
async def status() -> dict:
    return {"ownerExists": auth.owner_exists()}


@router.post("/register")
async def register(payload: RegisterIn) -> dict:
    user = auth.register_owner(payload.name, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OWNER_EXISTS",
                "message": "An owner account already exists. Sign in instead.",
            },
        )
    login_result = auth.login(payload.email, payload.password)
    if login_result is None:
        raise HTTPException(status_code=500, detail={"code": "SESSION_FAILED"})
    return {
        "ok": True,
        **login_result,
        "note": "Store the deviceToken in the Android app (Settings → Device token). It is shown only once here.",
    }


@router.post("/login")
async def login(payload: LoginIn) -> dict:
    result = auth.login(payload.email, payload.password)
    if result is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "BAD_CREDENTIALS", "message": "Wrong email or password."},
        )
    return {"ok": True, **result}


@router.get("/me")
async def me(authorization: Optional[str] = Header(default=None)) -> dict:
    user = auth.authenticate_request_headers(authorization)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED"})
    return {"user": {"name": user["name"], "email": user["email"]}}


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(default=None)) -> dict:
    token = (
        authorization[7:].strip()
        if (authorization or "").lower().startswith("bearer ")
        else ""
    )
    return {"ok": auth.logout(token)}
