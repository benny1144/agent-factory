from __future__ import annotations

import json
from pathlib import Path


def verify_entries() -> None:
    log_path = Path("logs/compliance/model_usage.jsonl")
    if not log_path.exists():
        raise SystemExit("No compliance log found at logs/compliance/model_usage.jsonl")
    with log_path.open("r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    entries = [json.loads(l) for l in lines]
    ok = True
    seen = {"Forgewright": False, "Librarius": False}
    for e in entries:
        agent = e.get("agent")
        if agent in seen:
            model = e.get("model")
            if model not in ("gpt-5-mini", "oss-safeguard"):
                ok = False
                print(f"❌ Unexpected model for {agent}: {model}")
            else:
                seen[agent] = True
    if not all(seen.values()):
        ok = False
        print(f"❌ Missing entries for agents: {[k for k,v in seen.items() if not v]}")
    if ok:
        print("✅ Verified compliance entries for Forgewright & Librarius")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    verify_entries()
