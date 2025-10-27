import os
import json
import time
import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATE_FILE = DATA_DIR / "genesis_state.json"
SESSION_LOGS = sorted(LOGS_DIR.glob("genesis_session_*.log"))
BUILD_LOG = LOGS_DIR / "genesis_build_requests.jsonl"

REFRESH_INTERVAL = 3  # seconds


def clear():
    """Cross-platform clear screen."""
    os.system("cls" if os.name == "nt" else "clear")


def read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def tail_file(path: Path, n=10):
    """Read last N lines of a file safely."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        try:
            f.seek(-2000, os.SEEK_END)
        except OSError:
            f.seek(0)
        lines = f.read().decode(errors="ignore").splitlines()
    return lines[-n:]


def render_header(state):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print("╔════════════════════════════════════════════════════╗")
    print("║                GENESIS LIVE MONITOR                ║")
    print("╠════════════════════════════════════════════════════╣")
    print(f"  Time:          {now}")
    print(f"  State:         {state.get('state', 'unknown')}")
    print(f"  Active:        {state.get('active', False)}")
    print(f"  Mode:          {state.get('mode', 'N/A')}")
    print(f"  Updated:       {state.get('updated', 'N/A')}")
    print("╠════════════════════════════════════════════════════╣")


def render_payload_summary():
    if not BUILD_LOG.exists():
        print("  No build requests logged yet.")
        return
    try:
        with open(BUILD_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()[-3:]
            print("  Recent Build Requests:")
            for ln in lines:
                try:
                    payload = json.loads(ln).get("payload", {})
                    name = payload.get("agent_name", "?")
                    purpose = payload.get("purpose", "")[:40]
                    print(f"    • {name}: {purpose}...")
                except Exception:
                    pass
    except Exception as e:
        print(f"  Error reading build log: {e}")


def render_logs():
    log_file = SESSION_LOGS[-1] if SESSION_LOGS else None
    if not log_file or not log_file.exists():
        print("  No session logs yet.")
        return
    print("  Recent Session Log:")
    for line in tail_file(log_file, n=8):
        print("   ", line)
    print("╚════════════════════════════════════════════════════╝")


def main():
    print("[Genesis Monitor] Watching logs and state...")
    if not STATE_FILE.exists():
        print("[WARN] No genesis_state.json found. Start Genesis first.")
        return

    while True:
        state = read_json(STATE_FILE)
        clear()
        render_header(state)
        render_payload_summary()
        print("╠════════════════════════════════════════════════════╣")
        render_logs()
        time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
