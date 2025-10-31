from __future__ import annotations

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / 'src'))

from utils.procedural_memory_pg import init_db  # type: ignore
from utils.memory_consistency_daemon import check_once  # type: ignore


def test_consistency_daemon_on_empty_db(tmp_path, monkeypatch):
    # Use isolated sqlite DB
    db_file = tmp_path / "daemon.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    init_db()

    rep = check_once(threshold=0.85)
    assert 0.0 <= rep.coherence <= 1.0
    assert rep.ingest_total >= 0
    assert rep.memory_inserts >= 0
    # On empty DB there should be no corrections (coherence defaults to 1.0)
    assert rep.corrections in (0, 1)
