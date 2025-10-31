from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request

# Repo-root aware paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "genesis_state.json"
BUILD_LOG = LOGS_DIR / "genesis_build_requests.jsonl"

app = FastAPI(title="Genesis API")


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"state": "error"}
    return {"state": "idle", "active": False}


def _save_state(st: Dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "genesis-api"}


@app.post("/build_agent")
async def build_agent(request: Request) -> Dict[str, Any]:
    """Receive a build request payload for Genesis.

    This endpoint appends the payload to a JSONL log and marks the state file
    with the latest requested action for offline processing by Genesis.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    rec: Dict[str, Any] = {
        "payload": payload,
        "env": {
            "actor": "GenesisAPI",
        },
    }
    try:
        with BUILD_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

    st = _load_state()
    st.update({
        "last_request": "build_agent",
        "last_payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
        "updated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "active": True,
    })
    _save_state(st)

    return {"ok": True, "received": True, "state": st.get("state", "idle")}


@app.get("/ping")
def ping() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/status")
def status() -> Dict[str, Any]:
    st = _load_state()
    return {
        "state": st.get("state"),
        "active": bool(st.get("active", False)),
        "updated": st.get("updated"),
    }

if __name__ == "__main__":
    import uvicorn, sys, argparse
    from pathlib import Path
    from datetime import datetime, timezone
    import json as _json

    # --- Ensure repo root in path ---
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # CLI for health ping used by Orion
    parser = argparse.ArgumentParser(description="Genesis API CLI")
    parser.add_argument("--ping", action="store_true", help="Print pong and exit (also logs event)")
    args, _unknown = parser.parse_known_args()

    LOGS_DIR = PROJECT_ROOT / "logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _genesis_log = LOGS_DIR / "genesis_activity.jsonl"

    if args.ping:
        try:
            with _genesis_log.open("a", encoding="utf-8") as f:
                f.write(_json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "event": "ping", "source": "genesis_api", "ok": True}) + "\n")
            # Mirror to governance event bus
            try:
                import uuid as _uuid
                _event_bus = PROJECT_ROOT / "governance" / "event_bus.jsonl"
                with _event_bus.open("a", encoding="utf-8") as bf:
                    bf.write(_json.dumps({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "agent": "Genesis",
                        "type": "ping",
                        "status": "ok",
                        "trace_id": _uuid.uuid4().hex
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
        except Exception:
            pass
        print("pong")
        raise SystemExit(0)

    print("[Genesis API] Starting listener on port 5055...")
    uvicorn.run(
        "factory_agents.architect_genesis.api:app",
        host="0.0.0.0",
        port=5055,
        reload=False,
        log_level="info",
    )
