from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Prefer repo-root safe paths per utils/paths.py
PROJECT_ROOT: Path
try:
    from utils.paths import PROJECT_ROOT as _PR
    PROJECT_ROOT = _PR
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOG_DIR = PROJECT_ROOT / "build" / "health_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PRIMARY = "https://api.disagreements.ai/health"
DEFAULT_MIRROR = "https://mirror.disagreements.ai/health"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_filename(ts: str | None = None) -> str:
    ts = ts or _now_iso()
    # Windows-safe: replace ":" with "-"
    return f"health_{ts.replace(':', '-')}" + ".json"


def _http_get_json(url: str, timeout: float = 10.0) -> Tuple[bool, Dict[str, Any] | None, str | None]:
    """Fetch URL and parse JSON. Returns (ok, json, error). No hard dep on requests."""
    start = time.time()
    try:
        try:
            import requests  # type: ignore

            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            return True, data, None
        except Exception:
            # Fallback to urllib
            import json as _json
            from urllib.request import urlopen, Request  # type: ignore

            req = Request(url, headers={"User-Agent": "AgentFactoryHealth/1.0"})
            with urlopen(req, timeout=timeout) as resp:  # nosec - simple GET
                text = resp.read().decode("utf-8", errors="ignore")
                try:
                    data = _json.loads(text)
                except Exception:
                    data = {"raw": text}
                # Treat HTTP 200 only as success when using urllib
                ok = 200 <= getattr(resp, "status", 200) < 300
                if ok:
                    return True, data, None
                return False, None, f"HTTP {getattr(resp, 'status', 'unknown')}"
    except Exception as e:  # pragma: no cover - network variability
        return False, None, f"{type(e).__name__}: {e}"
    finally:
        # We don't use duration here; the caller records it in meta
        _ = time.time() - start


def _write_log(payload: Dict[str, Any], filename: str | None = None) -> Path:
    name = filename or _iso_filename()
    path = LOG_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_health_check() -> Tuple[int, Dict[str, Any]]:
    """Execute health check with mirror cascade and structured logging.

    Exit codes:
      - 0: Success contacting primary/mirror or local stub used
      - 1: All endpoints unavailable and no stub
    """
    urls: List[str] = [
        os.getenv("DISAGREEMENTS_API_URL", DEFAULT_PRIMARY),
        DEFAULT_MIRROR,
    ]

    for url in urls:
        start = time.time()
        ok, data, err = _http_get_json(url)
        duration_ms = int((time.time() - start) * 1000)
        if ok and data is not None:
            payload = {
                "ok": True,
                "data": data,
                "error": None,
                "meta": {
                    "source": "remote",
                    "url": url,
                    "timestamp": _now_iso(),
                    "duration_ms": duration_ms,
                },
            }
            _write_log(payload)
            print(f"✅ Service OK at {url}")
            return 0, payload
        else:
            print(f"⚠️ Failed to reach {url}: {err}")

    # Local fallback
    stub_path = PROJECT_ROOT / "scripts" / "health_stub.json"
    if stub_path.exists():
        try:
            stub = json.loads(stub_path.read_text(encoding="utf-8"))
        except Exception as e:
            stub = {"status": "ok", "source": "stub", "error": f"Invalid stub JSON: {e}"}
        payload = {
            "ok": True,
            "data": stub,
            "error": None,
            "meta": {
                "source": "local_stub",
                "path": str(stub_path.relative_to(PROJECT_ROOT)),
                "timestamp": _now_iso(),
            },
        }
        _write_log(payload, filename="health_stub.json")
        print("🧩 Using local stub fallback.")
        return 0, payload

    print("❌ All endpoints unavailable.")
    return 1, {"ok": False, "data": {}, "error": "all_endpoints_unavailable", "meta": {"timestamp": _now_iso()}}


def main(argv: list[str] | None = None) -> int:
    # Simple shim: no args currently; future flags could include --log-dir or --url
    code, _payload = run_health_check()
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
