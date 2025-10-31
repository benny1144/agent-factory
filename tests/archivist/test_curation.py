from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.versioning_helper import get_next_version  # type: ignore


def test_get_next_version_pattern(tmp_path: Path):
    # Create a temp curated dir structure
    curated = tmp_path / "knowledge_base" / "curated"
    curated.mkdir(parents=True, exist_ok=True)
    # Point helper at this temp path by passing a prefix string
    prefix = curated / "curated_entry"
    # No existing versions → expect v01
    v1 = get_next_version(str(prefix))
    assert v1.endswith("_v01.md"), v1
    # Create v01 and v02, then expect v03
    (curated / "curated_entry_v01.md").write_text("a", encoding="utf-8")
    (curated / "curated_entry_v02.md").write_text("b", encoding="utf-8")
    v3 = get_next_version(str(prefix))
    assert v3.endswith("_v03.md"), v3
