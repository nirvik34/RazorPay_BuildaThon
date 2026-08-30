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


import socket
import threading
import json
import urllib.request

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in host_ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def run_udp_discovery(port: int = 8000, discovery_port: int = 8001):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.bind(("0.0.0.0", discovery_port))
    except Exception:
        return
    sock.settimeout(1.0)
    
    lan_ip = get_lan_ip()
    msg = f"AGENTPAY_GUARD_SERVER:http://{lan_ip}:{port}".encode("utf-8")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if b"AGENTPAY_GUARD_DISCOVER" in data:
                sock.sendto(msg, addr)
        except socket.timeout:
            try:
                sock.sendto(msg, ("255.255.255.255", discovery_port))
            except Exception:
                pass
        except Exception:
            break


import asyncio
from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

async def start_zeroconf_service(port: int = 8000):
    try:
        local_ip = get_lan_ip()
        packed_ip = socket.inet_aton(local_ip)
        
        info = ServiceInfo(
            "_friday-hub._tcp.local.",
            "FRIDAY Compute Hub._friday-hub._tcp.local.",
            addresses=[packed_ip],
            port=port,
            properties={"path": "/health", "service": "agentpay-guard"},
        )
        
        aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        await aiozc.zeroconf.async_register_service(info, allow_name_change=True)
        print(f"[Discovery] Advertising FRIDAY Hub mDNS at {local_ip}:{port}")
        return aiozc, info
    except Exception as e:
        print(f"[Discovery] Zeroconf register warning: {e}")
        return None, None


async def publish_ntfy_relay(port: int = 8000):
    topic = "agentpay_guard_hub_relay"
    while True:
        try:
            target_url = None
            # 1. Check ngrok local API
            try:
                req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        tunnels = data.get("tunnels", [])
                        for t in tunnels:
                            public_url = t.get("public_url")
                            if public_url:
                                target_url = public_url
                                break
            except Exception:
                pass

            # 2. Fallback to LAN IP
            if not target_url:
                lan_ip = get_lan_ip()
                if lan_ip and lan_ip != "127.0.0.1":
                    target_url = f"http://{lan_ip}:{port}"

            if target_url:
                req = urllib.request.Request(
                    f"https://ntfy.sh/{topic}",
                    data=target_url.encode("utf-8"),
                    headers={"Title": "AgentPay Guard Hub URL"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    pass
        except Exception:
            pass

        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    t = threading.Thread(target=run_udp_discovery, args=(settings.port, 8001), daemon=True)
    t.start()
    
    aiozc, zc_info = await start_zeroconf_service(settings.port)
    ntfy_task = asyncio.create_task(publish_ntfy_relay(settings.port))
    yield
    
    ntfy_task.cancel()
    if aiozc and zc_info:
        try:
            await aiozc.zeroconf.async_unregister_service(zc_info)
            await aiozc.async_close()
        except Exception:
            pass
    store.save()


app = FastAPI(title="AgentPay Guard API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
        if not auth.owner_exists():
            return await call_next(request)
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
