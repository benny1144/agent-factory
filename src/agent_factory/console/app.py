from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from utils.telemetry import TELEMETRY_DIR, summarize_metrics
from .api import router as compliance_router
from .api_routes import router as ui_router

# New integrated intelligence & observability routers
from agent_factory.api import gpt_router as gpt_router
from agent_factory.api import telemetry_router as telemetry_router

# Prometheus metrics exporter
try:
    from prometheus_client import make_asgi_app
except Exception:  # pragma: no cover
    make_asgi_app = None  # type: ignore

app = FastAPI(title="Agent Factory Governance Console")

# Enable permissive CORS for UI access (restrict in production as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Mount Prometheus metrics exporter if available
if make_asgi_app:
    app.mount("/metrics", make_asgi_app())


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



@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "Agent Factory Console Active"
