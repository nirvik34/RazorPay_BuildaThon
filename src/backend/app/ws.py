from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

CONNECTIONS: set[WebSocket] = set()


async def broadcast(event_type: str, payload: dict[str, Any]) -> None:
    message = json.dumps({"type": event_type, **payload})
    dead: list[WebSocket] = []
    for ws in list(CONNECTIONS):
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CONNECTIONS.discard(ws)


def broadcast_sync(event_type: str, payload: dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast(event_type, payload))
    except RuntimeError:
        pass
