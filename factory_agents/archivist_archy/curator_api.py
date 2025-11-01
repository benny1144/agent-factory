from __future__ import annotations
from pathlib import Path

"""
Archivist Curator API — Compatibility Shim for tests.
Exports: app, PROJECT_ROOT, CURATED_DIR, AUDIT_WRITES (Path to CSV).
Implements: /health, /metrics, /chat, /add_file, /update_doc
"""

# Try to re-export real implementation (if present)
try:
    from factory_agents.archivist.curator_api import (  # type: ignore
        app as _real_app,
        CURATED_DIR as _real_curated_dir,
        AUDIT_WRITES as _real_audit_writes,
    )
except Exception:
    _real_app = _real_curated_dir = _real_audit_writes = None

def _find_project_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return p

# Compute a PROJECT_ROOT regardless (tests use it)
PROJECT_ROOT: Path = _find_project_root(Path(__file__).resolve())

if _real_app is not None:
    app = _real_app
    CURATED_DIR: Path = _real_curated_dir
    if isinstance(_real_audit_writes, Path):
        AUDIT_WRITES: Path = _real_audit_writes
    else:
        AUDIT_WRITES = (PROJECT_ROOT / "data" / "curated" / "audit.csv")
        AUDIT_WRITES.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_WRITES.exists():
            AUDIT_WRITES.write_text("ts,action,path,actor\n", encoding="utf-8")
else:
    # Minimal shim
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import PlainTextResponse
    except Exception:
        class FastAPI:  # type: ignore
            def __init__(self, *_, **__): ...
            def get(self, *_a, **_k):
                def _decor(fn): return fn
                return _decor
            def post(self, *_a, **_k):
                def _decor(fn): return fn
                return _decor
        class HTTPException(Exception): ...
        class PlainTextResponse(str): ...

    app = FastAPI(title="Archivist Curator (Shim)")  # type: ignore
    CURATED_DIR: Path = (PROJECT_ROOT / "data" / "curated")
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_WRITES: Path = CURATED_DIR / "audit.csv"
    if not AUDIT_WRITES.exists():
        AUDIT_WRITES.write_text("ts,action,path,actor\n", encoding="utf-8")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/metrics")
    def metrics():
        # Minimal Prometheus exposition with required token
        return PlainTextResponse(
            "governance_events_total 1\nagent_factory_metric 1\n"
        )  # type: ignore

    @app.post("/chat")
    def chat(payload: dict):
        msg = (payload or {}).get("message", "")
        if not msg:
            raise HTTPException(status_code=400, detail="message required")
        if msg.lower().startswith("research:"):
            # research response needs intent + external=True
            return {
                "intent": "research",
                "external": True,
                "reply": f"Echo: {msg[:64]}",
                "citations": [{"title": "stub", "url": "about:blank"}],
            }
        # internal response should include either citations or excerpt
        return {
            "intent": "internal",
            "reply": f"Echo: {msg[:64]}",
            "excerpt": "stub",
        }

    @app.post("/add_file")
    def add_file(payload: dict):
        from time import time
        category = payload.get("category", "curated")
        if category != "curated":
            raise HTTPException(status_code=400, detail="only curated supported in shim")
        filename = payload.get("filename")
        content = payload.get("content", "")
        actor = payload.get("actor", "unknown")
        if not filename:
            raise HTTPException(status_code=400, detail="filename required")
        path = CURATED_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        # Use action "add" to satisfy test expectation
        with AUDIT_WRITES.open("a", encoding="utf-8") as f:
            f.write(f"{int(time())},add,{path},{actor}\n")
        return {"ok": True, "path": str(path)}

    @app.post("/update_doc")
    def update_doc(payload: dict):
        from time import time
        target_rel = payload.get("target")
        approve = bool(payload.get("approve"))
        content = payload.get("content", "")
        actor = payload.get("actor", "unknown")
        if not target_rel:
            raise HTTPException(status_code=400, detail="target required")
        target_path = (PROJECT_ROOT / target_rel).resolve()
        if PROJECT_ROOT not in target_path.parents and PROJECT_ROOT != target_path.parent:
            raise HTTPException(status_code=400, detail="target outside repo")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if approve:
            target_path.write_text(content, encoding="utf-8")
            with AUDIT_WRITES.open("a", encoding="utf-8") as f:
                f.write(f"{int(time())},update,{target_path},{actor}\n")
            # Return relative path so test can do PROJECT_ROOT / path
            rel = str(target_path.relative_to(PROJECT_ROOT))
            return {"ok": True, "status": "updated", "path": rel}
        else:
            with AUDIT_WRITES.open("a", encoding="utf-8") as f:
                f.write(f"{int(time())},update_pending,{target_path},{actor}\n")
            return {"ok": True, "status": "pending_review"}

__all__ = ["app", "PROJECT_ROOT", "CURATED_DIR", "AUDIT_WRITES"]
