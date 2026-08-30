from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from ..config import settings


class RazorpayError(Exception):
    pass


def _auth() -> tuple[str, str]:
    return (settings.razorpay_key_id, settings.razorpay_key_secret)


async def create_order(authorization: dict[str, Any]) -> dict[str, Any]:
    amount_paise = int(authorization["amount"] * 100)
    if settings.razorpay_live:
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": authorization["authorizationId"],
            "notes": {
                "agentId": authorization.get("agentId", ""),
                "requestId": authorization.get("requestId", ""),
                "merchant": authorization.get("merchant", ""),
                "destinationSeller": authorization.get("merchant", "").title(),
                "product": authorization.get("product", ""),
            },
        }
        async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
            resp = await client.post("https://api.razorpay.com/v1/orders", json=payload)
            if resp.status_code >= 400:
                raise RazorpayError(
                    f"Razorpay order failed: {resp.status_code} {resp.text[:200]}"
                )
            return resp.json()
    await asyncio_sleep()
    return {
        "id": f"order_sim_{uuid.uuid4().hex[:10]}",
        "amount": amount_paise,
        "currency": "INR",
        "status": "created",
        "simulated": True,
        "receipt": authorization["authorizationId"],
    }


async def fetch_payment(payment_id: str) -> dict[str, Any]:
    """Fetch a payment directly from Razorpay (live keys required)."""
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.get(f"https://api.razorpay.com/v1/payments/{payment_id}")
        if resp.status_code >= 400:
            raise RazorpayError(
                f"Fetch payment failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json()


async def capture_payment_by_id(payment_id: str, amount_paise: int) -> dict[str, Any]:
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        cap = await client.post(
            f"https://api.razorpay.com/v1/payments/{payment_id}/capture",
            json={"amount": amount_paise, "currency": "INR"},
        )
        if cap.status_code >= 400:
            raise RazorpayError(f"Capture failed: {cap.status_code} {cap.text[:200]}")
        return cap.json()


async def finalize_payment(order: dict[str, Any]) -> dict[str, Any]:
    """After checkout: capture an authorized payment, or report pending state."""
    if order.get("simulated"):
        await asyncio_sleep()
        return {
            "id": f"pay_sim_{uuid.uuid4().hex[:10]}",
            "status": "captured",
            "order_id": order["id"],
            "simulated": True,
        }
    try:
        async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
            list_resp = await client.get(
                f"https://api.razorpay.com/v1/orders/{order['id']}/payments"
            )
            items = (
                list_resp.json().get("items", []) if list_resp.status_code < 400 else []
            )
        if not items:
            return {"id": None, "status": "awaiting_checkout", "order_id": order["id"]}
        latest = items[0]
        if latest["status"] == "authorized":
            return await capture_payment_by_id(latest["id"], order["amount"])
        return {
            "id": latest["id"],
            "status": latest["status"],
            "method": latest.get("method"),
            "order_id": order["id"],
        }
    except httpx.HTTPError as exc:
        raise RazorpayError(f"Finalize failed: {exc}") from exc


async def capture_payment(order: dict[str, Any]) -> dict[str, Any]:
    if not order.get("simulated"):
        payment_id = None
        try:
            async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
                list_resp = await client.get(
                    f"https://api.razorpay.com/v1/orders/{order['id']}/payments"
                )
                if list_resp.status_code < 400:
                    items = list_resp.json().get("items", [])
                    if items:
                        payment_id = items[0]["id"]
            if payment_id:
                async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
                    cap = await client.post(
                        f"https://api.razorpay.com/v1/payments/{payment_id}/capture",
                        json={"amount": order["amount"], "currency": "INR"},
                    )
                    if cap.status_code < 400:
                        return cap.json()
        except httpx.HTTPError as exc:
            raise RazorpayError(f"Capture failed: {exc}") from exc
        return {
            "id": payment_id or f"pay_unknown",
            "status": "processing",
            "order_id": order["id"],
        }
    await asyncio_sleep()
    return {
        "id": f"pay_sim_{uuid.uuid4().hex[:10]}",
        "status": "captured",
        "order_id": order["id"],
        "simulated": True,
    }


async def asyncio_sleep() -> None:
    import asyncio

    await asyncio.sleep(0.3)
