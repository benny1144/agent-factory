from __future__ import annotations
import asyncio, json, signal, sys
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from rich.table import Table

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
GOV_EVENT_BUS = ROOT / "governance" / "event_bus.jsonl"
GOV_EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)
INTERVAL_SECONDS = 600  # 10 minutes
AGENTS = ["artisan", "orion", "watchtower", "archivist", "librarius", "genesis"]

console = Console()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_heartbeat(agent: str):
    """Write heartbeat entry to runtime log."""
    log_path = LOGS_DIR / agent / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"{now_iso()} HEARTBEAT {agent}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    return log_path


def emit_governance_event(agent: str, msg: str):
    """Emit event for the governance audit bus."""
    event = {
        "ts": now_iso(),
        "agent": agent,
        "type": "heartbeat",
        "details": {"message": msg},
    }
    with open(GOV_EVENT_BUS, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


async def inject_heartbeats():
    """Main coroutine: periodically inject heartbeats for all agents."""
    while True:
        table = Table(title=f"Automated Heartbeats — {now_iso()}")
        table.add_column("Agent", style="bold cyan")
        table.add_column("Status", style="bold green")
        table.add_column("Log Path", style="dim")

        for agent in AGENTS:
            path = write_heartbeat(agent)
            emit_governance_event(agent, "automated heartbeat")
            table.add_row(agent, "✅ injected", str(path.relative_to(ROOT)))

        console.print(table)
        console.print(f"[green]Next heartbeat cycle in {INTERVAL_SECONDS/60:.0f} minutes.[/green]\n")

        await asyncio.sleep(INTERVAL_SECONDS)


def stop_signal_handler(sig, frame):
    console.print(f"[yellow]Received {signal.Signals(sig).name}, shutting down heartbeat scheduler...[/yellow]")
    sys.exit(0)


def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, stop_signal_handler)
    signal.signal(signal.SIGTERM, stop_signal_handler)

    console.print(f"[bold cyan]Starting heartbeat scheduler at {now_iso()}[/bold cyan]")
    console.print(f"[dim]Agents: {', '.join(AGENTS)}[/dim]\n")

    try:
        asyncio.run(inject_heartbeats())
    except KeyboardInterrupt:
        console.print("[yellow]KeyboardInterrupt: Stopping gracefully.[/yellow]")


if __name__ == "__main__":
    main()
