"""
Payload Sender for Genesis Build Requests
-----------------------------------------
Validates and sends agent creation payloads to the Genesis API endpoint.
Handles response logging, audit trail writing, and error recovery.
"""

from __future__ import annotations
import json
import sys
import requests
from pathlib import Path
from datetime import datetime
from subprocess import run, PIPE

# === CONFIGURATION ===
GENESIS_PORT = 5055
GENESIS_URL = f"http://localhost:{GENESIS_PORT}/build_agent"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
PAYLOADS_DIR = PROJECT_ROOT / "payloads"
VALIDATOR = PROJECT_ROOT / "tools/payload_validator.py"
LOGS_DIR.mkdir(exist_ok=True, parents=True)
AUDIT_LOG = LOGS_DIR / "payload_sender_audit.log"

def run_validator(payload_file: Path):
    """Run the payload validator before sending."""
    print(f"[Genesis Sender] Running validator on {payload_file.name}...")
    result = run(
        [sys.executable, str(VALIDATOR), str(payload_file)],
        text=True,
        stdout=PIPE,
        stderr=PIPE
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        sys.exit(f"[ERROR] Validation failed for {payload_file.name}.")
    print(result.stdout)
    print("[OK] Validation passed.\n")

def send_payload(payload_file: Path):
    """Send the validated payload to Genesis API."""
    print(f"[Genesis Sender] Sending {payload_file.name} to Genesis ({GENESIS_URL}) ...")

    try:
        with open(payload_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"[ERROR] Could not read payload file: {e}")

    try:
        response = requests.post(
            GENESIS_URL,
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        print(f"[OK] Response received: {json.dumps(result, indent=2)}")
        audit(payload_file, True, result)
        return True
    except requests.exceptions.ConnectionError:
        sys.exit("[ERROR] Could not connect to Genesis API. Is it running on port 5055?")
    except requests.exceptions.Timeout:
        sys.exit("[ERROR] Request timed out while contacting Genesis.")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"[ERROR] HTTP error from Genesis: {e}")
    except Exception as e:
        sys.exit(f"[ERROR] Unexpected error: {e}")

def audit(payload_file: Path, success: bool, response: dict | None = None):
    """Write audit event to log."""
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload_file.name,
        "success": success,
        "response": response or {}
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tools/payload_sender.py <payload_filename.json>")

    payload_file = Path(sys.argv[1])
    if not payload_file.exists():
        sys.exit(f"[ERROR] Payload file not found: {payload_file}")

    run_validator(payload_file)
    send_payload(payload_file)

if __name__ == "__main__":
    main()
