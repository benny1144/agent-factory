from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

try:
    from agent_factory.utils.telemetry import TELEMETRY_DIR, summarize_metrics
except ImportError:
    # Fallback for refactored telemetry layout
    from agent_factory.utils.telemetry import summarize_metrics
    try:
        from agent_factory.utils.paths import LOGS_DIR as TELEMETRY_DIR
    except ImportError:
        import os
        from pathlib import Path
        TELEMETRY_DIR = Path(os.getcwd()) / "logs"

# Ensure the TELEMETRY_DIR path exists before startup
from pathlib import Path as _Path
if not isinstance(TELEMETRY_DIR, _Path):
    TELEMETRY_DIR = _Path(TELEMETRY_DIR)
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
print(f"[Init] TELEMETRY_DIR → {TELEMETRY_DIR}")
from .api import router as compliance_router
from .api_routes import router as ui_router
from .health import router as health_router

# New integrated intelligence & observability routers
from agent_factory.api import gpt_router as gpt_router
from agent_factory.api import telemetry_router as telemetry_router
from agent_factory.api import federation_router as federation_router

# Prometheus metrics exporter
try:
    from prometheus_client import make_asgi_app
except Exception:  # pragma: no cover
    make_asgi_app = None  # type: ignore

app = FastAPI(title="Agent Factory Governance Console")

# CORS origins aligned with UI (Render + local dev + custom domain + legacy Cloud Run)
origins = [
    "https://agent-factory-ui.onrender.com",
    "http://localhost:5173",
    "https://dashboard.agent-factory.dev",
    # keep legacy Cloud Run UI origin for backward compatibility
    "https://agent-factory-ui-1092120039663.us-central1.run.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing compliance routes (mounted under /api)
app.include_router(compliance_router, prefix="/api", tags=["compliance"])
# UI/API routes already include "/api/..." in their path definitions
app.include_router(ui_router)
# Mount GPT assistant and telemetry websocket routers
app.include_router(gpt_router)
app.include_router(telemetry_router)
# Mount Federation router
app.include_router(federation_router)
# Mount health router
app.include_router(health_router)

# Mount Prometheus metrics exporter if available
if make_asgi_app:
    app.mount("/metrics", make_asgi_app())

# Phase 40.6: Watchtower static dashboard mount (if built)
from pathlib import Path as _P
_WT_DIST = _P("frontend") / "watchtower" / "dist"
try:
    if _WT_DIST.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(_WT_DIST), html=True),
            name="watchtower",
        )
        print(f"[Watchtower] Mounted static dashboard at /dashboard from {_WT_DIST}")
    else:
        @app.get("/dashboard")
        def _watchtower_placeholder() -> HTMLResponse:  # type: ignore[override]
            return HTMLResponse("""
            <html><head><title>Watchtower</title></head>
            <body style='font-family: system-ui'>
              <h1>Watchtower Dashboard</h1>
              <p>Watchtower UI loaded successfully</p>
              <p>Static build not found at <code>frontend/watchtower/dist</code>.</p>
              <p>Run <code>npm --prefix frontend/watchtower ci --omit=dev && npm --prefix frontend/watchtower run build</code> then redeploy.</p>
            </body></html>
            """)
except Exception as _e:
    print(f"[Watchtower] Static mount skipped: {_e}")

# Phase 40.6: Include Watchtower API endpoints
try:
    from agent_factory.api.watchtower_endpoints import router as watchtower_router
    app.include_router(watchtower_router, prefix="/api")
    print("[Watchtower] API endpoints mounted under /api")
except Exception as _e:
    print(f"[Watchtower] API router include skipped: {_e}")

# Phase 40.6: Startup federation health verification
try:
    from agent_factory.utils.heartbeat import ensure_heartbeats

    @app.on_event("startup")
    async def _phase_40_6_startup():
        try:
            ensure_heartbeats()
            print("[Startup] Federation health verified ✅")
        except Exception as e:
            print(f"[Startup] Health init failed: {e}")
except Exception as _e:
    print(f"[Watchtower] Heartbeat import skipped: {_e}")


@app.get("/", response_class=PlainTextResponse)
def index() -> str:
    return "Agent Factory Console Active"


@app.get("/console", response_class=HTMLResponse)
def console_index() -> str:
    summary = summarize_metrics()
    html = "<h1>Governance Console — Agent Factory</h1>"
    html += "<h2>Telemetry Summary</h2><pre>" + json.dumps(summary, indent=2) + "</pre>"
    html += "<p>Endpoints: <code>/drift</code>, <code>/optimization</code>, <code>/api/audit</code></p>"
    return html


@app.get("/drift")
def get_drift() -> dict:
    path = TELEMETRY_DIR / "ethical_drift.jsonl"
    if not path.exists():
        return {"message": "No drift data"}
    try:
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        lines = []
    return {"count": len(lines), "records": lines[-10:]}


@app.get("/optimization")
def get_optimization() -> dict:
    path = TELEMETRY_DIR / "optimization_adjustment.jsonl"
    if not path.exists():
        return {"message": "No optimization data"}
    try:
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        lines = []
    return {"count": len(lines), "records": lines[-10:]}


# Simple echo WebSocket for connectivity tests
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Connection accepted on /ws")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WS] WebSocket message received: {data}")
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        # client disconnected
        print("[WS] Client disconnected from /ws")
        pass


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "agent-factory-console"}


# Render health check endpoint
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agent-factory-console"}

# --- Compatibility: expose /metrics if not already defined ---
try:
    from fastapi.responses import PlainTextResponse  # type: ignore
except Exception:
    PlainTextResponse = None  # type: ignore

if "app" in globals() and PlainTextResponse is not None:
    try:
        # only add if route missing
        existing = {r.path for r in app.router.routes}  # type: ignore
        if "/metrics" not in existing:
            @app.get("/metrics")
            def _compat_metrics():
                return PlainTextResponse("agent_factory_metric 1\n")  # type: ignore
    except Exception:
        pass
