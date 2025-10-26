from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / ".venv"
REQ_FILE = REPO_ROOT / "requirements.txt"


def _run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> None:
    # 1) Create venv if missing
    if not VENV_DIR.exists():
        rc = _run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if rc != 0:
            sys.exit(rc)

    # 2) Resolve venv python path cross-platform
    if platform.system().lower().startswith("win"):
        py = VENV_DIR / "Scripts" / "python.exe"
        pip = [str(py), "-m", "pip"]
    else:
        py = VENV_DIR / "bin" / "python"
        pip = [str(py), "-m", "pip"]

    if not py.exists():
        print(f"[ERROR] Could not locate venv python at {py}")
        sys.exit(1)

    # 3) Upgrade pip and install requirements
    rc = _run(pip + ["install", "--upgrade", "pip"])
    if rc != 0:
        sys.exit(rc)

    if not REQ_FILE.exists():
        print(f"[WARN] {REQ_FILE} not found — skipping dependency install.")
        print("You can install manually using: pip install pytest sqlalchemy fastapi prometheus-client python-dotenv uvicorn httpx")
        sys.exit(0)

    rc = _run(pip + ["install", "-r", str(REQ_FILE)])
    if rc != 0:
        sys.exit(rc)

    print("\n[OK] Virtual environment ready at .venv and dependencies installed.")
    print("Next steps in IntelliJ/PyCharm:")
    print(" - File → Settings → Project → Python Interpreter → Add → Existing environment → select .venv/python")
    print(" - Reopen requirements.txt to verify no missing-package warnings remain.")


if __name__ == "__main__":
    main()
