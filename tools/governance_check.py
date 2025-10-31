from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = REPO_ROOT / "governance"
AGENTS_REG = GOV_DIR / "agents_registry.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        # Fallback: naïve JSON attempt
        try:
            return json.loads(path.read_text(encoding="utf-8"))  # type: ignore
        except Exception:
            return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def validate() -> int:
    problems: list[str] = []
    if not AGENTS_REG.exists():
        problems.append("agents_registry_missing")
    else:
        data = _load_yaml(AGENTS_REG)
        agents = data.get("agents") if isinstance(data, dict) else None
        if not isinstance(agents, list) or not agents:
            problems.append("agents_registry_empty")
        else:
            # Basic schema check for each agent record
            for i, a in enumerate(agents):
                if not isinstance(a, dict):
                    problems.append(f"agent_{i}_invalid")
                    continue
                for key in ("name", "type", "level"):
                    if key not in a:
                        problems.append(f"agent_{i}_missing_{key}")

    if problems:
        print("[FAIL] Governance check issues:")
        for p in problems:
            print(" -", p)
        return 1

    print("[OK] Governance check passed.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Governance Check")
    p.add_argument("--validate", action="store_true", help="Validate governance configs and registry")
    ns = p.parse_args()
    if ns.validate:
        sys.exit(validate())
    p.print_help()


if __name__ == "__main__":
    main()
