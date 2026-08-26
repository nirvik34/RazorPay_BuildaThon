from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_agent, routes_auth, routes_data, routes_guard, routes_mcp, routes_simulation
from . import auth
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_agent.router)
app.include_router(routes_guard.router)
app.include_router(routes_data.router)
app.include_router(routes_simulation.router)
app.include_router(routes_mcp.router)
app.include_router(routes_auth.router)


PROTECTED_PREFIXES = (
    "/agents",
    "/policies",
    "/transactions",
    "/audit",
    "/intents",
    "/simulate",
    "/guard/agents",
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if request.method != "OPTIONS" and any(
        path == p or path.startswith(p + "/") for p in PROTECTED_PREFIXES
    ):
        user = auth.authenticate_request_headers(request.headers.get("authorization"))
        if not user:
            response = JSONResponse(
                {"detail": {"code": "UNAUTHENTICATED", "message": "Sign in at /login"}},
                status_code=401,
            )
            origin = request.headers.get("origin", "")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Vary"] = "Origin"
            return response
    return await call_next(request)


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
