from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

AUDIT_PREFIX = "[AUDIT] "


@dataclass
class Args:
    root: Path
    registry: Path
    audit_dir: Path
    fix: bool


def parse_args() -> Args:
    p = argparse.ArgumentParser(description="Validate Knowledge Base Registry and provenance hashes")
    p.add_argument("--root", default=".", help="Repository root directory")
    p.add_argument("--registry", default="registry/metadata_index.json", help="Path to registry JSON file")
    p.add_argument("--audit-dir", default="validation/logs", help="Directory to write audit logs into")
    p.add_argument("--fix", action="store_true", help="Write back computed sha256 provenance hashes")
    ns = p.parse_args()
    return Args(root=Path(ns.root), registry=Path(ns.registry), audit_dir=Path(ns.audit_dir), fix=bool(ns.fix))


def _normalize_path(root: Path, file_path: str) -> Path:
    # Treat leading "/" as repo-root relative, not filesystem root
    rel = file_path[1:] if file_path.startswith("/") else file_path
    return (root / rel).resolve()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256-" + h.hexdigest()


def _load_registry(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Registry must be a JSON array of entries")
    return data


def _write_registry(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _audit_log(audit_dir: Path, event_type: str, metadata: Dict[str, Any]) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_path = audit_dir / "kba_validation.log"
    record = {
        "ok": True,
        "data": {"event_type": event_type, "metadata": metadata},
        "error": None,
        "meta": {
            "source": "kba_validator",
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(AUDIT_PREFIX + json.dumps(record, ensure_ascii=False) + "\n")


def validate(args: Args) -> Tuple[bool, bool, List[str]]:
    if not args.registry.exists():
        print(f"[FAIL] Registry not found: {args.registry}")
        return False, False, ["registry_missing"]

    try:
        entries = _load_registry(args.registry)
    except Exception as e:
        print(f"[FAIL] Invalid registry JSON: {e}")
        return False, False, ["registry_invalid"]

    missing_files: List[str] = []
    updated = False

    for ent in entries:
        file_path = ent.get("file_path")
        if not isinstance(file_path, str):
            print(f"[FAIL] Entry missing file_path: {ent}")
            _audit_log(args.audit_dir, "kba_entry_invalid", {"id": ent.get("id"), "reason": "no_file_path"})
            continue
        abs_path = _normalize_path(args.root, file_path)
        if not abs_path.exists():
            print(f"[FAIL] Missing file: {file_path}")
            _audit_log(args.audit_dir, "kba_missing_file", {"id": ent.get("id"), "file_path": file_path})
            missing_files.append(file_path)
            continue

        # Compute hash
        sha = _sha256(abs_path)
        prev = ent.get("provenance")
        if prev != sha:
            _audit_log(args.audit_dir, "kba_provenance_mismatch", {
                "id": ent.get("id"),
                "file_path": file_path,
                "prev": prev,
                "new": sha,
            })
            if args.fix:
                ent["provenance"] = sha
                updated = True
        else:
            _audit_log(args.audit_dir, "kba_provenance_ok", {"id": ent.get("id"), "file_path": file_path})

    # If fix requested and changes made, write back
    if args.fix and updated:
        _write_registry(args.registry, entries)
        print("[OK] Registry provenance updated.")

    files_ok = len(missing_files) == 0
    prov_ok = True
    if not args.fix:
        # When not fixing, provenance is OK only if no mismatches were detected
        # Recompute to check mismatches succinctly
        prov_ok = True
        for ent in entries:
            fp = ent.get("file_path")
            if not isinstance(fp, str):
                prov_ok = False
                continue
            ap = _normalize_path(args.root, fp)
            if not ap.exists():
                continue  # already accounted in files_ok
            if ent.get("provenance") != _sha256(ap):
                prov_ok = False
                break

    summary = {
        "files_ok": files_ok,
        "provenance_ok": prov_ok if not args.fix else True,
        "fixed": args.fix and updated,
    }
    _audit_log(args.audit_dir, "kba_validation_summary", summary)

    if not files_ok or (not args.fix and not prov_ok):
        return files_ok, prov_ok, missing_files
    return True, True, []


def main() -> None:
    args = parse_args()
    files_ok, prov_ok, missing = validate(args)
    print(json.dumps({"files_ok": files_ok, "provenance_ok": prov_ok, "missing": missing}, indent=2))
    if not files_ok or not prov_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
