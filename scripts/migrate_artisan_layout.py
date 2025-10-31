from __future__ import annotations

"""Best-effort migration for Artisan layout (Phase 38.8)

- Moves legacy folders to canonical locations if they exist:
  - artisanExecs/ -> factory_agents/artisan_executor/runtime/
  - ARTISAN_LOG/, artisanLog/ -> logs/artisan/
- No-op if sources are absent.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

legacy_execs = ROOT / "artisanExecs"
legacy_logs_a = ROOT / "ARTISAN_LOG"
legacy_logs_b = ROOT / "artisanLog"

runtime_dest = ROOT / "factory_agents" / "artisan_executor" / "runtime"
logs_dest = ROOT / "logs" / "artisan"

runtime_dest.mkdir(parents=True, exist_ok=True)
logs_dest.mkdir(parents=True, exist_ok=True)

moved = []

if legacy_execs.exists():
    for p in legacy_execs.iterdir():
        target = runtime_dest / p.name
        try:
            if p.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.move(str(p), str(target))
            else:
                shutil.move(str(p), str(target))
            moved.append(str(target))
        except Exception:
            pass
    try:
        legacy_execs.rmdir()
    except Exception:
        pass

for src in (legacy_logs_a, legacy_logs_b):
    if src.exists():
        for p in src.iterdir():
            target = logs_dest / p.name
            try:
                if p.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.move(str(p), str(target))
                else:
                    shutil.move(str(p), str(target))
                moved.append(str(target))
            except Exception:
                pass
        try:
            src.rmdir()
        except Exception:
            pass

print("✅ Migration complete. Moved:")
for m in moved:
    print(" -", m)
