from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_agent, routes_data, routes_guard, routes_mcp, routes_simulation
from .config import settings
from .ws import CONNECTIONS
from .state import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    yield
    store.save()


app = FastAPI(title="AgentPay Guard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_agent.router)
app.include_router(routes_guard.router)
app.include_router(routes_data.router)
app.include_router(routes_simulation.router)
app.include_router(routes_mcp.router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "mode": "razorpay-live" if settings.razorpay_live else "razorpay-simulated",
        "agents": len(store.snapshot()["agents"]),
    }


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    CONNECTIONS.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        CONNECTIONS.discard(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
