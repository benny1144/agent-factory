from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from tools.logging_utils import JsonlLogger
from utils.paths import PROJECT_ROOT, LOGS_DIR, TASKS_COMPLETE_DIR

SPEC_PATH = PROJECT_ROOT / "tasks" / "from_expert" / "Junie_DUNI_Tunnel_Autoheal_Setup.json"
CLOUD_CONFIG = PROJECT_ROOT / ".cloudflared" / "config.yml"
WATCHDOG_PS1 = PROJECT_ROOT / "watchdog.ps1"
TASK_XML_BRIDGE = PROJECT_ROOT / "automation" / "tasks" / "JunieBridge_Expert.xml"
TASK_XML_WATCHDOG = PROJECT_ROOT / "automation" / "tasks" / "Junie_Watchdog.xml"
BRIDGE_SCRIPT = PROJECT_ROOT / "scripts" / "start_junie_bridge.py"
ADMIN_STEPS_TXT = PROJECT_ROOT / "automation" / "tasks" / "ADMIN_STEPS.txt"
STATUS_OUT = TASKS_COMPLETE_DIR / "Junie_DUNI_Tunnel_Autoheal_Setup.status.json"
VALIDATION_LOG = LOGS_DIR / "duni_task_validation.log"

EXPECTED_TUNNEL_ID = "6a6523c4-6712-4c3e-83b8-ce9a31867997"
EXPECTED_CREDS = r"C:\\Users\\benny\\.cloudflared\\6a6523c4-6712-4c3e-83b8-ce9a31867997.json"
EXPECTED_HOSTNAME = "gpt.disagreements.ai"
EXPECTED_SERVICE = "http://127.0.0.1:8000"
EXPECTED_ROOT = r"C:\\Users\\benny\\IdeaProjects\\agent-factory"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _append_log_line(p: Path, line: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def load_spec() -> Dict:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_file_exists(path: Path) -> bool:
    return path.exists()


def validate_cloudflared_config() -> Dict:
    ok = False
    details: Dict[str, object] = {}
    try:
        text = CLOUD_CONFIG.read_text(encoding="utf-8")
        # Normalize potential double backslashes to single for comparison
        text_norm = text.replace("\\\\", "\\")
        expected_creds_single = EXPECTED_CREDS.replace("\\\\", "\\")
        has_tunnel = (f"tunnel: {EXPECTED_TUNNEL_ID}" in text) or (f"tunnel: {EXPECTED_TUNNEL_ID}" in text_norm)
        has_credentials = (f"credentials-file: {EXPECTED_CREDS}" in text) or (f"credentials-file: {expected_creds_single}" in text) or (f"credentials-file: {expected_creds_single}" in text_norm)
        has_hostname = (f"hostname: {EXPECTED_HOSTNAME}" in text) or (f"hostname: {EXPECTED_HOSTNAME}" in text_norm)
        has_service = (f"service: {EXPECTED_SERVICE}" in text) or (f"service: {EXPECTED_SERVICE}" in text_norm)
        ok = has_tunnel and has_credentials and has_hostname and has_service
        details = {
            "has_tunnel": has_tunnel,
            "has_credentials": has_credentials,
            "has_hostname": has_hostname,
            "has_service": has_service,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": ok, **details}


def main() -> int:
    logger = JsonlLogger()

    # Begin validation
    results: Dict[str, object] = {
        "ts": _now_iso(),
        "task": "Junie_DUNI_Tunnel_Autoheal_Setup",
        "expected_root": EXPECTED_ROOT,
        "project_root": str(PROJECT_ROOT),
    }

    # Basic file existence checks
    checks: List[Dict[str, object]] = []
    paths_to_check = [
        ("cloud_config", CLOUD_CONFIG),
        ("watchdog_ps1", WATCHDOG_PS1),
        ("task_xml_bridge", TASK_XML_BRIDGE),
        ("task_xml_watchdog", TASK_XML_WATCHDOG),
        ("bridge_script", BRIDGE_SCRIPT),
    ]
    for name, p in paths_to_check:
        exists = check_file_exists(p)
        checks.append({"name": name, "path": str(p), "exists": exists})

    results["checks"] = checks

    # Content validation for cloudflared config
    cfg_check = validate_cloudflared_config()
    results["cloudflared_config"] = cfg_check

    # External credentials presence (outside repo): warn-only
    ext_creds = Path(EXPECTED_CREDS)
    results["external_credentials_present"] = ext_creds.exists()

    # Determine overall OK
    exists_ok = all(x["exists"] for x in checks)  # type: ignore[index]
    cfg_ok = bool(cfg_check.get("ok"))
    overall_ok = exists_ok and cfg_ok
    results["ok"] = overall_ok

    # Write human-readable validation log
    _append_log_line(VALIDATION_LOG, f"[{_now_iso()}] Validation {'OK' if overall_ok else 'FAILED'}")
    for c in checks:
        _append_log_line(VALIDATION_LOG, f" - {c['name']}: {'OK' if c['exists'] else 'MISSING'} -> {c['path']}")
    _append_log_line(VALIDATION_LOG, f" - cloudflared config check: {'OK' if cfg_ok else 'INVALID'}")
    if not results["external_credentials_present"]:
        _append_log_line(VALIDATION_LOG, f" - WARNING: External credentials not found at {EXPECTED_CREDS}")

    # Log JSONL
    logger.log(overall_ok, {"event": "duni_setup_validation", **results})

    # On success, write status file and admin steps
    if overall_ok:
        STATUS_OUT.parent.mkdir(parents=True, exist_ok=True)
        _write_text(
            STATUS_OUT,
            json.dumps(
                {
                    "task": "Junie_DUNI_Tunnel_Autoheal_Setup",
                    "status": "complete",
                    "ts": _now_iso(),
                    "notes": {
                        "external_credentials_present": results["external_credentials_present"],
                    },
                },
                indent=2,
            ),
        )
        admin_text = (
            "✅ Junie_DUNI_Tunnel_Autoheal_Setup complete. Please run the following steps manually as Administrator:\n\n"
            "0) Start the Agent Factory backend API locally (new port 8000):\n"
            "   cd C:\\Users\\benny\\IdeaProjects\\agent-factory\n"
            "   $env:PYTHONPATH=\".\\src\"; python -m uvicorn agent_factory.server.fastapi_server:app --host 127.0.0.1 --port 8000 --reload\n\n"
            "1) Recreate and start Cloudflared service:\n"
            "   sc.exe delete Cloudflared\n"
            "   sc.exe create Cloudflared binPath= \"\\\"C:\\Program Files (x86)\\cloudflared\\cloudflared.exe\\\" tunnel run gpt\" start=auto\n"
            "   Set-Service -Name Cloudflared -StartupType AutomaticDelayedStart\n"
            "   net start Cloudflared\n\n"
            "2) Import tasks:\n"
            "   schtasks /create /tn \"JunieBridge_Expert\" /xml \"C:\\Users\\benny\\IdeaProjects\\agent-factory\\automation\\tasks\\JunieBridge_Expert.xml\"\n"
            "   schtasks /create /tn \"Junie_Watchdog\" /xml \"C:\\Users\\benny\\IdeaProjects\\agent-factory\\automation\\tasks\\Junie_Watchdog.xml\"\n\n"
            "3) Verify health (local and public):\n"
            "   curl http://127.0.0.1:8000/health\n"
            "   curl -v https://gpt.disagreements.ai/health\n"
        )
        _write_text(ADMIN_STEPS_TXT, admin_text)
        print(admin_text)
    else:
        print("Validation failed. See logs/duni_task_validation.log for details.")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
