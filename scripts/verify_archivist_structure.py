from __future__ import annotations

import json
import sys
from pathlib import Path

base = Path("factory_agents/archivist_archy")
expected = ["main.py", "reasoning_core.py", "fastapi_server.py", "persona_archivist.yaml"]
missing = [f for f in expected if not (base / f).exists()]

report = {"archivist_archy": {"missing": missing, "status": "ok" if not missing else "incomplete"}}
path = Path("governance/audits/archivist_structure.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("✅ Archivist structure verification complete →", path)
sys.exit(0 if not missing else 1)
