from __future__ import annotations
import json, argparse, asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any
import sys, site
site.main()  # manually load site-packages
from rich.console import Console
from rich.table import Table

# === Path Setup ===
ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
EVENT_BUS = ROOT / "governance" / "event_bus.jsonl"
AUDIT_LOG = ROOT / "logs" / "governance" / "health_checks.jsonl"

for p in [LOGS, AUDIT_LOG.parent]:
    p.mkdir(parents=True, exist_ok=True)

console = Console()

# === Core Helpers ===
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def emit_event(agent: str, evt_type: str, details: dict | None = None):
    rec = {
        "ts": utc_now(),
        "agent": agent,
        "type": evt_type,
        "details": details or {},
    }
    with open(EVENT_BUS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

def audit(service: str, ok: bool, meta: dict | None = None):
    rec = {
        "ts": utc_now(),
        "service": service,
        "ok": ok,
        "meta": meta or {},
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

# === Health Logic ===
def check_runtime_log(service: str) -> tuple[bool, str]:
    """Return (ok, message) by checking log freshness & heartbeat content."""
    log_path = LOGS / service / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Auto-heal missing log
    if not log_path.exists():
        log_path.write_text(f"{utc_now()} INIT {service} runtime log\n", encoding="utf-8")
        return False, "no heartbeat yet"

    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        return False, "empty log"

    last = lines[-1]
    try:
        ts = datetime.fromisoformat(last.split()[0].replace("Z", "+00:00"))
    except Exception:
        ts = datetime.now(timezone.utc) - timedelta(days=1)

    recent = datetime.now(timezone.utc) - ts < timedelta(minutes=5)
    ok = ("ok" in last.lower() or "healthy" in last.lower()) and recent
    return ok, last.strip()

def check_event_bus(service: str) -> tuple[bool, str]:
    """If no recent heartbeat in log, fallback to event bus activity."""
    if not EVENT_BUS.exists():
        return False, "no event bus"
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    with open(EVENT_BUS, "r", encoding="utf-8") as f:
        for line in reversed(f.readlines()[-100:]):  # last 100 events
            try:
                evt = json.loads(line)
                if evt.get("agent", "").lower() == service.lower():
                    ts = datetime.fromisoformat(evt["ts"].replace("Z", "+00:00"))
                    if ts >= cutoff:
                        return True, "recent event"
            except Exception:
                continue
    return False, "stale or no events"

async def check_service(service: str) -> tuple[str, bool, str]:
    ok, msg = check_runtime_log(service)
    if not ok:
        evt_ok, evt_msg = check_event_bus(service)
        ok, msg = evt_ok, evt_msg
    audit(service, ok, {"details": msg})
    emit_event("Artisan", "health_check", {"service": service, "ok": ok})
    return service, ok, msg

# === Federation Health Runner ===
async def run_all() -> int:
    services = ["artisan", "orion", "watchtower", "archivist", "librarius", "genesis"]
    results = []
    for svc in services:
        res = await check_service(svc)
        results.append(res)

    table = Table(title=f"Federation Health Report — {utc_now()} UTC")
    table.add_column("Service", justify="left")
    table.add_column("Status", justify="center")
    table.add_column("Details", justify="left")

    unhealthy = []
    for svc, ok, msg in results:
        status = "✅ Healthy" if ok else "❌ Unhealthy"
        if not ok:
            unhealthy.append(svc)
        table.add_row(svc.capitalize(), status, msg)
    console.print(table)

    if unhealthy:
        console.print(f"[yellow]⚠️ One or more agents require attention: {', '.join(unhealthy)}[/yellow]")
        return 1
    console.print("[green]✅ All federation agents healthy[/green]")
    return 0

# === CLI Entrypoint ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", help="Check a specific service")
    parser.add_argument("--all", action="store_true", help="Check all services")
    args = parser.parse_args()

    if args.all:
        return asyncio.run(run_all())
    if args.service:
        svc, ok, msg = asyncio.run(check_service(args.service))
        console.print(f"{svc.capitalize()} → {'✅ Healthy' if ok else '❌ Unhealthy'} ({msg})")
        return 0 if ok else 1
    parser.print_help()
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
