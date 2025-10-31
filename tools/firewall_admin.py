from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def validate() -> int:
    """Best-effort Human Firewall validation.

    Checks for presence of core governance modules and risk matrix.
    Returns 0 on success, non-zero on failure.
    """
    problems: list[str] = []

    firewall_mod = REPO_ROOT / "utils" / "firewall_protocol.py"
    if not firewall_mod.exists():
        # Also check wrapped package path used in services
        alt = REPO_ROOT / "src" / "agent_factory" / "utils" / "firewall_protocol.py"
        if not alt.exists():
            problems.append("firewall_protocol_missing")

    risk_matrix = REPO_ROOT / "personas" / "risk_matrix.json"
    if not risk_matrix.exists():
        problems.append("risk_matrix_missing")

    if problems:
        print("[FAIL] Firewall validation issues:")
        for p in problems:
            print(" -", p)
        return 1

    print("[OK] Firewall validation passed.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Firewall Admin")
    p.add_argument("--validate", action="store_true", help="Run firewall validation checks")
    ns = p.parse_args()

    if ns.validate:
        code = validate()
        sys.exit(code)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
