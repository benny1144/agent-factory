from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Repo root paths
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
BACKUPS_DIR = REPO_ROOT / "backups"
LOGS_DIR = REPO_ROOT / "logs"
AUDIT_DIR = REPO_ROOT / "compliance" / "audit_log"
JUNIE_ACTIVITY = AUDIT_DIR / "junie_activity.csv"
CONFIG_DIR = REPO_ROOT / "config"
HUMAN_FIREWALL_YAML = CONFIG_DIR / "human_firewall.yaml"


TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check_hitl_flag() -> bool:
    """Return True if confirm_cleanup: true is set in config/human_firewall.yaml.

    CI override: if env PRE_FLIGHT_ASSUME_CONFIRM is true, proceed.
    """
    if str(os.getenv("PRE_FLIGHT_ASSUME_CONFIRM", "false")).lower() == "true":
        return True
    if not HUMAN_FIREWALL_YAML.exists():
        return False
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(HUMAN_FIREWALL_YAML.read_text(encoding="utf-8")) or {}
        return bool(str(data.get("confirm_cleanup", False)).lower() == "true")
    except Exception:
        # naive parse fallback
        try:
            text = HUMAN_FIREWALL_YAML.read_text(encoding="utf-8").lower()
            return "confirm_cleanup" in text and "true" in text
        except Exception:
            return False


def ensure_audit_files() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if not JUNIE_ACTIVITY.exists():
        _write(JUNIE_ACTIVITY, "ts,action,details\n")


def rotate_logs() -> Optional[Path]:
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return None
    archive = LOGS_DIR / "archive" / TS
    archive.parent.mkdir(parents=True, exist_ok=True)
    # move all items except archive/
    for item in LOGS_DIR.iterdir():
        if item.name == "archive":
            continue
        try:
            shutil.move(str(item), str(archive / item.name))
        except Exception:
            pass
    return archive


def env_audit() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"environment_audit_{TS}.txt"
    lines = []
    lines.append(f"timestamp: {TS}")
    lines.append(f"python: {sys.version.split()[0]}")
    lines.append(f"platform: {platform.platform()}")

    # venv detection (best-effort)
    venv = os.getenv("VIRTUAL_ENV") or (sys.prefix if "venv" in sys.prefix.lower() else "")
    lines.append(f"venv: {venv or 'unknown'}")

    # pip check
    try:
        res = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, timeout=60)
        lines.append("\n[pip check]\n" + (res.stdout.strip() or res.stderr.strip()))
    except Exception as e:
        lines.append(f"\n[pip check] error: {e}")

    # pip list --outdated
    try:
        res2 = subprocess.run([sys.executable, "-m", "pip", "list", "--outdated"], capture_output=True, text=True, timeout=120)
        lines.append("\n[pip list --outdated]\n" + res2.stdout.strip())
    except Exception as e:
        lines.append(f"\n[pip list --outdated] error: {e}")

    _write(out, "\n".join(lines) + "\n")
    return out


def main() -> None:
    # 1) Branch safety & git bundle are operator tasks; print guidance
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    print("[PREFLIGHT] For backup run: git bundle create ./backups/preflight_" + TS + ".bundle --all")
    print("[PREFLIGHT] Verify with: git verify-bundle ./backups/preflight_" + TS + ".bundle")

    # 2) Governance sanity checks
    try:
        res_fw = subprocess.run([sys.executable, "tools/firewall_admin.py", "--validate"], check=False)
        res_gov = subprocess.run([sys.executable, "tools/governance_check.py", "--validate"], check=False)
        if res_fw.returncode != 0 or res_gov.returncode != 0:
            print("[PREFLIGHT] Governance validation failed; inspect output above.")
    except Exception as e:
        print(f"[PREFLIGHT] Governance validation error: {e}")

    # 3) Ensure audit CSV exists
    ensure_audit_files()

    # 4) Rotate logs
    archive = rotate_logs()
    if archive:
        print(f"[PREFLIGHT] Logs rotated to {archive}")

    # 5) Environment audit
    report = env_audit()
    print(f"[PREFLIGHT] Environment audit written to {report}")

    # 6) HITL confirmation
    if not check_hitl_flag():
        print("[PREFLIGHT] HITL confirm required. Set confirm_cleanup: true in config/human_firewall.yaml")
        sys.exit(2)

    # 7) Record action in junie_activity
    try:
        with JUNIE_ACTIVITY.open("a", encoding="utf-8") as f:
            f.write(f"{TS},preflight_ok,env_report={report.as_posix()}\n")
    except Exception:
        pass

    print("[PREFLIGHT] Completed successfully and HITL confirm present.")


if __name__ == "__main__":
    main()
