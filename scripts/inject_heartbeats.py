from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Initialize console
console = Console()

# Define root and agent list
ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
GOV_EVENT_BUS = ROOT / "governance" / "event_bus.jsonl"
GOV_EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)

AGENTS = ["artisan", "orion", "watchtower", "archivist", "librarius", "genesis"]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def log_heartbeat(agent: str) -> Path:
    """Inject a heartbeat line into the agent’s runtime log."""
    log_path = LOGS_DIR / agent / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"{now_iso()} HEARTBEAT {agent}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    return log_path

def emit_governance_event(agent: str, msg: str):
    """Emit an event for governance auditing."""
    event = {
        "ts": now_iso(),
        "agent": agent,
        "type": "heartbeat",
        "details": {"message": msg},
    }
    with open(GOV_EVENT_BUS, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def main():
    table = Table(title=f"Heartbeat Injection — {now_iso()}")
    table.add_column("Agent", style="bold cyan")
    table.add_column("Status", style="bold green")
    table.add_column("Log Path", style="dim")

    for agent in AGENTS:
        path = log_heartbeat(agent)
        emit_governance_event(agent, "manual heartbeat injected")
        table.add_row(agent, "✅ injected", str(path.relative_to(ROOT)))

    console.print(table)
    console.print("[green]All heartbeats successfully injected.[/green]")

if __name__ == "__main__":
    main()
