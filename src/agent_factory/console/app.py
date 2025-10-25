from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from utils.telemetry import TELEMETRY_DIR, summarize_metrics
from .api import router as compliance_router

app = FastAPI(title="Agent Factory Governance Console")
app.include_router(compliance_router, prefix="/api", tags=["compliance"])


@app.get("/", response_class=HTMLResponse)
def index() -> str:
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
