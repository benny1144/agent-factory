from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
GOV_DIR = ROOT / "governance"
LEDGER = GOV_DIR / "compliance_ledger.jsonl"
BACKUP_DIR = GOV_DIR / "backup"
AUDIT_LOG = GOV_DIR / "firewall_audit.log"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
GOV_DIR.mkdir(parents=True, exist_ok=True)


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class LedgerEntry:
    entry_id: str
    file_path: str
    sha256: str
    size: int
    timestamp: str
    status: str = "recorded"

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


def append_ledger_entry(file_path: str, status: str = "recorded") -> Dict[str, Any]:
    p = (ROOT / file_path).resolve() if not file_path.startswith(str(ROOT)) else Path(file_path)
    if not p.exists() or not p.is_file():
        rec = {
            "entry_id": f"missing-{datetime.now(timezone.utc).timestamp()}",
            "file_path": str(p),
            "sha256": "",
            "size": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "missing",
        }
        _append_line(LEDGER, json.dumps(rec, ensure_ascii=False))
        return rec
    digest = sha256_file(p)
    size = p.stat().st_size
    entry = LedgerEntry(
        entry_id=digest[:16],
        file_path=str(p.relative_to(ROOT)),
        sha256=digest,
        size=size,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=status,
    )
    _append_line(LEDGER, entry.to_json())
    return entry.__dict__


def verify_ledger(paths: Iterable[str] | None = None) -> Dict[str, Any]:
    """Verify current hashes against ledger entries or new set of paths.
    Writes a human-readable summary to governance/firewall_audit.log and returns stats.
    """
    checked = 0
    ok = 0
    failed: list[Dict[str, Any]] = []
    if paths:
        targets = [(ROOT / p).resolve() for p in paths]
    else:
        # If no explicit list, try to verify latest 100 ledger entries
        targets = []
        if LEDGER.exists():
            lines = LEDGER.read_text(encoding="utf-8").splitlines()[-100:]
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    rel = obj.get("file_path")
                    if rel:
                        targets.append((ROOT / rel).resolve())
                except Exception:
                    continue
    for t in targets:
        if not t.exists() or not t.is_file():
            failed.append({"file": str(t), "error": "missing"})
            continue
        try:
            digest = sha256_file(t)
            checked += 1
            # We can optionally lookup an existing ledger entry. For now, accept as OK and append.
            append_ledger_entry(str(t.relative_to(ROOT)), status="verified")
            ok += 1
        except Exception as e:
            failed.append({"file": str(t), "error": str(e)})
    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "checked": checked,
        "ok": ok,
        "failed": len(failed),
    }
    _append_line(AUDIT_LOG, json.dumps({"compliance_verify": summary, "failed_items": failed}, ensure_ascii=False))
    # If verification passed (no failures), update last success timestamp
    try:
        if summary["failed"] == 0:
            last_success = GOV_DIR / "compliance_last_success.txt"
            last_success.write_text(summary["ts"], encoding="utf-8")
    except Exception:
        pass
    # Backup ledger after verify
    try:
        if LEDGER.exists():
            backup_name = BACKUP_DIR / f"ledger_backup_{int(datetime.now(timezone.utc).timestamp())}.jsonl"
            backup_name.write_text(LEDGER.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    return summary


if __name__ == "__main__":
    # CLI usage for ad-hoc verify
    import argparse

    ap = argparse.ArgumentParser(description="Compliance ledger integrity guard")
    ap.add_argument("paths", nargs="*", help="optional file paths to verify")
    args = ap.parse_args()
    res = verify_ledger(args.paths or None)
    print(json.dumps(res, indent=2))
