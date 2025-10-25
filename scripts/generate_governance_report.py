from __future__ import annotations

import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Repo-root aware
REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
DATA_DIR = REPO_ROOT / "data"


def _load_latest_digest() -> Dict[str, Any]:
    files = sorted(ARTIFACTS_DIR.glob("audit_digest_*.json"))
    if not files:
        return {}
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_baseline_meta() -> Dict[str, Any]:
    candidates = [DATA_DIR / "ethical_baseline.json", DATA_DIR / "ethical_baseline_v2.json"]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return {"path": str(p), "meta": {k: v for k, v in data.items() if k != "vectors"}, "vector_count": len(data.get("vectors", []))}
            except Exception:
                pass
    return {"path": None, "meta": {}, "vector_count": 0}


def _load_governance_events() -> Dict[str, Any]:
    # Best-effort DB import
    try:
        import sys
        sys.path.append(str(REPO_ROOT))
        sys.path.append(str(REPO_ROOT / "src"))
        from utils.procedural_memory_pg import init_db, select_all, governance_events  # type: ignore
    except Exception:
        return {"count": 0, "events": []}

    try:
        init_db()
        rows = select_all(governance_events)
        # Show recent 10
        return {"count": len(rows), "events": rows[-10:] if rows else []}
    except Exception:
        return {"count": 0, "events": []}


def generate_report() -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = ARTIFACTS_DIR / f"governance_report_{ts}.md"

    digest = _load_latest_digest()
    baseline = _load_baseline_meta()
    gov = _load_governance_events()

    lines: List[str] = []
    lines.append("# Governance Report — Continuous Oversight")
    lines.append(f"Generated: {ts}")
    lines.append("")
    lines.append("## Summary")
    lines.append("- Daily audit digest present: " + ("yes" if digest else "no"))
    lines.append(f"- Governance events total: {gov['count']}")
    lines.append(f"- Baseline vectors: {baseline.get('vector_count', 0)} (file: {baseline.get('path')})")
    lines.append("")

    lines.append("## Latest Audit Digest")
    lines.append("```json")
    lines.append(json.dumps(digest, indent=2, ensure_ascii=False) if digest else "{}")
    lines.append("```")
    lines.append("")

    lines.append("## Baseline Metadata")
    lines.append("```json")
    lines.append(json.dumps(baseline, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Recent Governance Events")
    lines.append("```json")
    lines.append(json.dumps(gov.get("events", []), indent=2, ensure_ascii=False))
    lines.append("```")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[GOV-REPORT] Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    generate_report()
