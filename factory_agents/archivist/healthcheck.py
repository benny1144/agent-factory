# Archivist Healthcheck (Phase 9)
from __future__ import annotations
import os
import datetime
import importlib
from typing import List

try:
    import dotenv  # type: ignore
except Exception:  # optional
    dotenv = None  # type: ignore

# Optional risk logger
try:
    from factory_agents.archivist import reasoning_core as _rc_h
except Exception:
    _rc_h = None  # type: ignore


DIRECTORIES: List[str] = [
    "logs",
    "knowledge_base",
    "registry",
    "compliance",
    "memory_store",
]

DEPENDENCIES: List[str] = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "dotenv",
    "sqlalchemy",
    "httpx",
    "openai",
    "requests",
    "yaml",
    "numpy",
]

ENV_FILE = "factory_config/api_keys.env"


def run_health_diagnostics() -> str:
    """Perform a comprehensive system health check for Archivist.
    Returns a Markdown-formatted report and writes to logs/health_audit.log.
    """
    results: List[str] = []
    timestamp = datetime.datetime.utcnow().isoformat()

    # Directory checks
    for d in DIRECTORIES:
        if os.path.exists(d):
            results.append(f"✅ Directory found: {d}")
        else:
            results.append(f"❗ Missing directory: {d}")

    # Dependency checks (best-effort)
    for dep in DEPENDENCIES:
        modname = dep.replace("-", "_")
        try:
            importlib.import_module(modname)
            results.append(f"✅ Dependency OK: {dep}")
        except ImportError:
            results.append(f"⚠️ Missing dependency: {dep}")

    # API key checks
    if dotenv is not None:
        try:
            dotenv.load_dotenv(ENV_FILE)
        except Exception:
            pass
    api_keys = ["OPENAI_API_KEY", "SERPER_API_KEY", "GEMINI_API_KEY"]
    for key in api_keys:
        if os.getenv(key):
            results.append(f"✅ API Key loaded: {key}")
        else:
            results.append(f"⚠️ Missing API Key: {key}")

    # Write health report
    os.makedirs("logs", exist_ok=True)
    report_path = os.path.join("logs", "health_audit.log")
    with open(report_path, "a", encoding="utf-8") as log:
        log.write(f"[HEALTH CHECK] {timestamp}\n" + "\n".join(results) + "\n---\n")

    # Risk hook (diagnostics considered Low)
    try:
        if _rc_h is not None:
            _rc_h.risk_assess("diagnostics", f"dirs={len(DIRECTORIES)} deps={len(DEPENDENCIES)}")
    except Exception:
        pass

    formatted = "\n".join(results)
    return f"🜂 **Archivist Health Report**\n## Timestamp: {timestamp}\n{formatted}"
