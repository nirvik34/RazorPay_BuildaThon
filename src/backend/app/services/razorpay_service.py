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
                "agentId": authorization["agentId"],
                "requestId": authorization["requestId"],
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
