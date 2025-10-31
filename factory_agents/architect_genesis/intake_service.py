from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI

# Repo-root aware paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "genesis_state.json"

app = FastAPI(title="Genesis Intake Service")


def _read_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"state": "error"}
    return {"state": "idle", "active": False}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "genesis-intake"}


@app.get("/ping")
def ping() -> Dict[str, Any]:
    # Minimal liveness ping for health monitor
    return {"ok": True}


@app.get("/status")
def status() -> Dict[str, Any]:
    st = _read_state()
    # Minimal payload for operators/clients
    return {
        "state": st.get("state"),
        "active": bool(st.get("active", False)),
        "mode": st.get("mode"),
        "listening": bool(st.get("listening", False)),
        "listen_port": st.get("listen_port"),
        "updated": st.get("updated"),
    }
