from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, inspect, text

# Prefer repo-root absolute default matching utils.procedural_memory_pg
try:
    # Ensure repo imports work when run from CI or root
    REPO_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(REPO_ROOT))
    sys.path.append(str(REPO_ROOT / "src"))
    from utils.paths import PROJECT_ROOT, PROVENANCE_DIR
    from utils.procedural_memory_pg import init_db  # to ensure tables exist
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    PROVENANCE_DIR = PROJECT_ROOT / "knowledge_base" / "provenance"
    def init_db():
        return None

DEFAULT_SQLITE = f"sqlite:///{(PROJECT_ROOT / 'data' / 'agent_factory.sqlite').as_posix()}"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)


def validate_tables(engine) -> bool:
    # Ensure tables are initialized if using our utils
    try:
        init_db()
    except Exception:
        pass

    insp = inspect(engine)
    required = {"agent_runs", "memory_events", "knowledge_ingest"}
    existing = set(insp.get_table_names())
    missing = required - existing
    if missing:
        print(f"[FAIL] Missing tables: {', '.join(sorted(missing))}")
        return False
    print("[OK] All required tables exist.")
    return True


def _query_knowledge_sources(engine) -> list[str]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT source_path FROM knowledge_ingest")).fetchall()
            return [r[0] for r in rows]
    except Exception as e:
        print(f"[ERROR] Cannot query knowledge_ingest: {e}")
        return []


def validate_provenance(engine) -> bool:
    sources = _query_knowledge_sources(engine)
    # If there are no ingests yet, this check passes.
    if not sources:
        print("[OK] No knowledge_ingest rows found; skipping provenance check.")
        return True

    missing: list[Path] = []
    for src in sources:
        file_id = Path(src).stem
        prov_file = PROVENANCE_DIR / f"{file_id}.json"
        if not prov_file.exists():
            missing.append(prov_file)

    if missing:
        print(f"[FAIL] Missing provenance JSONs ({len(missing)}):")
        for f in missing:
            print(" -", f)
        return False

    print("[OK] All provenance JSONs present.")
    return True


def main() -> None:
    engine = create_engine(DB_URL, future=True)
    ok_tables = validate_tables(engine)
    ok_prov = validate_provenance(engine)
    summary = {"tables_ok": ok_tables, "provenance_ok": ok_prov}
    print(json.dumps(summary, indent=2))
    if not (ok_tables and ok_prov):
        sys.exit(1)


if __name__ == "__main__":
    main()
