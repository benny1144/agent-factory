from __future__ import annotations

"""
Knowledge Indexer & Watcher

- Scans the repository knowledge base under knowledge_base/ and maintains YAML index files:
  - knowledge_base/index/Core_Index.yaml
  - knowledge_base/index/Expansion_Index.yaml
  - knowledge_base/index/Agents_Index.yaml
  - knowledge_base/index/Federation_Map.yaml (reserved)

- CLI:
  python utils/knowledge_indexer.py --scan        # one-time scan/update
  python utils/knowledge_indexer.py --rebuild     # truncate indexes and rebuild
  python utils/knowledge_indexer.py --watch       # watch mode (watchdog if available, else polling)

- Public API:
  - scan() -> dict
  - refresh() -> dict (alias to scan)
  - watch(poll_interval_s: int = 5) -> None
  - ensure_agent_kb_tree(agent_name: str) -> dict

Notes:
- Uses utils.paths.PROJECT_ROOT for path safety (no reliance on CWD)
- Avoids hard dependency on PyYAML or watchdog; falls back gracefully if unavailable
- Logs JSONL actions to logs/knowledge_indexer.jsonl
- Writes provenance snapshot to logs/validation/knowledge_tree_init.json on first run
"""

import argparse
import dataclasses
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:  # watchdog is optional
    from watchdog.observers import Observer  # type: ignore
    from watchdog.events import FileSystemEventHandler  # type: ignore
except Exception:  # pragma: no cover
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore

# Path helpers
try:
    from utils.paths import PROJECT_ROOT, resolve_path
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    def resolve_path(file_path: str, base_dir: Path | None = None, allowed_roots: list[Path] | None = None) -> Path:  # type: ignore[override]
        base = base_dir or PROJECT_ROOT
        p = Path(file_path)
        resolved = (p if p.is_absolute() else (base / p)).resolve()
        if allowed_roots:
            roots = [Path(r).resolve() for r in allowed_roots]
            if not any(str(resolved).startswith(str(root)) for root in roots):
                raise PermissionError(f"Path not within allowed roots: {resolved}")
        return resolved

KB_DIR = PROJECT_ROOT / "knowledge_base"
INDEX_DIR = KB_DIR / "index"
LOGS_DIR = PROJECT_ROOT / "logs"
VALIDATION_DIR = LOGS_DIR / "validation"

CORE_INDEX = INDEX_DIR / "Core_Index.yaml"
EXPANSION_INDEX = INDEX_DIR / "Expansion_Index.yaml"
AGENTS_INDEX = INDEX_DIR / "Agents_Index.yaml"
FEDERATION_MAP = INDEX_DIR / "Federation_Map.yaml"

TRACE_LOG = LOGS_DIR / "knowledge_indexer.jsonl"
PROVENANCE_SNAPSHOT = VALIDATION_DIR / "knowledge_tree_init.json"
BACKUP_LOG = LOGS_DIR / "knowledge_routing_backup.jsonl"
DOCS_DIR = PROJECT_ROOT / "docs"


# --------------- IO helpers ---------------

def _ensure_dirs() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as f:
        f.write(content)
    tmp.replace(path)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if yaml:
            return yaml.safe_load(text) or {}
        # Fallback: try JSON parse if yaml missing but file content is json-like
        return json.loads(text)
    except Exception:
        return {}


def _dump_yaml(obj: dict) -> str:
    if yaml:
        try:
            return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)
        except Exception:
            pass
    # Fallback: write JSON text into .yaml (acceptable as a subset)
    return json.dumps(obj, ensure_ascii=False, indent=2)


# --------------- Hashing & metadata ---------------

def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _title_for_path(p: Path) -> str:
    # Derive title from filename or first line of text files
    name = p.stem.replace("_", " ").replace("-", " ").strip()
    if p.suffix.lower() in {".txt", ".md", ".py", ".json", ".yaml", ".yml"}:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip().strip("#").strip()
                if s:
                    # Prefer a heading-like line
                    return s[:120]
        except Exception:
            pass
    return name[:120] or p.name


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


# --------------- Index writing ---------------

def _init_if_missing() -> None:
    _ensure_dirs()
    defaults: list[tuple[Path, dict]] = [
        (CORE_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "items": []}),
        (EXPANSION_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "items": []}),
        (AGENTS_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "agents": []}),
        (FEDERATION_MAP, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "map": {}}),
    ]
    for path, obj in defaults:
        if not path.exists():
            _atomic_write(path, _dump_yaml(obj))


@dataclass
class IndexStats:
    core_added: int = 0
    core_updated: int = 0
    expansion_added: int = 0
    expansion_updated: int = 0
    agents_updated: int = 0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _upsert_item(items: list[dict], item: dict, key: str = "path") -> tuple[list[dict], bool]:
    updated = False
    existing_idx = None
    for i, it in enumerate(items):
        if it.get(key) == item.get(key):
            existing_idx = i
            break
    if existing_idx is None:
        items.append(item)
    else:
        items[existing_idx] = {**items[existing_idx], **item}
        updated = True
    return items, updated


def _route_index_for_path(p: Path) -> Optional[Path]:
    try:
        rel = p.resolve().relative_to(KB_DIR.resolve()).as_posix()
    except Exception:
        return None
    if rel.startswith("core/"):
        return CORE_INDEX
    if rel.startswith("expansion/"):
        return EXPANSION_INDEX
    if rel.startswith("agents/"):
        return AGENTS_INDEX
    return None


def _update_agents_index(agent_name: str) -> bool:
    obj = _load_yaml(AGENTS_INDEX) or {}
    agents = list(obj.get("agents") or [])
    root = KB_DIR / "agents" / agent_name
    rec = {
        "name": agent_name,
        "root": _repo_rel(root),
        "docs": _repo_rel(root / "docs"),
        "persona": _repo_rel(root / "persona"),
        "research": _repo_rel(root / "research"),
        "memory": _repo_rel(root / "memory"),
        "last_updated": _now_iso(),
    }
    agents, updated = _upsert_item(agents, rec, key="name")
    obj["agents"] = sorted(agents, key=lambda a: a.get("name", ""))
    obj["last_updated"] = _now_iso()
    _atomic_write(AGENTS_INDEX, _dump_yaml(obj))
    return updated


def ensure_agent_kb_tree(agent_name: str) -> dict:
    """Ensure agent knowledge tree exists and is registered in Agents_Index.yaml.

    Returns a dict with `{ok, created_dirs: int, updated_index: bool}`.
    """
    created = 0
    base = KB_DIR / "agents" / agent_name
    for sub in ("docs", "persona", "research", "memory"):
        p = base / sub
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created += 1
    updated_index = _update_agents_index(agent_name)
    _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "ensure_agent_kb_tree", "agent": agent_name, "created_dirs": created, "updated_index": updated_index})
    return {"ok": True, "created_dirs": created, "updated_index": updated_index}


def _provenance_snapshot_once() -> None:
    if PROVENANCE_SNAPSHOT.exists():
        return
    tree = {
        "ts": _now_iso(),
        "roots": {
            "core": _repo_rel(KB_DIR / "core"),
            "expansion": _repo_rel(KB_DIR / "expansion"),
            "agents": _repo_rel(KB_DIR / "agents"),
            "datasets": _repo_rel(KB_DIR / "datasets"),
            "validation": _repo_rel(KB_DIR / "validation"),
            "index": _repo_rel(KB_DIR / "index"),
        },
        "hashes": {},
    }
    # Hash directory listings for provenance (deterministic order)
    for sub in ("core", "expansion", "agents", "datasets", "validation"):
        d = KB_DIR / sub
        if d.exists():
            entries = sorted([_repo_rel(p) for p in d.rglob("*") if p.exists()])
            h = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
            tree["hashes"][sub] = h
    _atomic_write(PROVENANCE_SNAPSHOT, json.dumps(tree, ensure_ascii=False, indent=2))


def _scan_files(stats: IndexStats) -> IndexStats:
    # Core/Expansion files populate into their respective indexes
    for area, idx_path in (("core", CORE_INDEX), ("expansion", EXPANSION_INDEX)):
        base = KB_DIR / area
        if not base.exists():
            continue
        obj = _load_yaml(idx_path) or {}
        items = list(obj.get("items") or [])
        seen_paths = set()
        for p in base.rglob("*"):
            if p.is_dir():
                continue
            if p.is_relative_to(INDEX_DIR):  # skip index directory if within area by accident
                continue
            # Build record with extended schema (id/status backfilled)
            rec = {
                "id": hashlib.sha256(_repo_rel(p).encode("utf-8")).hexdigest()[:16],
                "title": _title_for_path(p),
                "path": _repo_rel(p),
                "version": "v1",
                "last_updated": _now_iso(),
                "indexed": True,
                "status": "active",
                "sha256": _sha256_file(p),
            }
            items, updated = _upsert_item(items, rec, key="path")
            if area == "core":
                if updated:
                    stats.core_updated += 1
                else:
                    stats.core_added += 1
            else:
                if updated:
                    stats.expansion_updated += 1
                else:
                    stats.expansion_added += 1
            seen_paths.add(rec["path"])
        # Optionally, prune entries that no longer exist
        items = [it for it in items if (PROJECT_ROOT / it.get("path", ".")).exists()]
        obj["items"] = sorted(items, key=lambda it: it.get("title", ""))
        obj["last_updated"] = _now_iso()
        _atomic_write(idx_path, _dump_yaml(obj))
    return stats


def scan() -> dict:
    """Scan knowledge_base and update YAML indices. Returns statistics.

    This function is idempotent and safe to run repeatedly.
    """
    _init_if_missing()
    _provenance_snapshot_once()
    stats = IndexStats()
    # Ensure the default agents are present and registered if their trees exist
    for agent in ("archivist", "genesis", "junie"):
        base = KB_DIR / "agents" / agent
        if base.exists():
            _update_agents_index(agent)
    stats = _scan_files(stats)
    res = {"ok": True, "data": stats.to_dict(), "error": None, "meta": {"ts": _now_iso()}}
    _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "scan", **res})
    return res


def refresh() -> dict:
    """Alias to scan(). Provided for API symmetry."""
    return scan()


# --------------- Watch mode ---------------
class _OnChangeHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, debounce_s: float = 1.0):
        super().__init__()
        self._last = 0.0
        self._debounce = debounce_s

    # watchdog calls different methods; handle generically
    def on_any_event(self, event):  # pragma: no cover - runtime behavior
        now = time.time()
        if now - self._last < self._debounce:
            return
        self._last = now
        try:
            scan()
        except Exception as e:
            _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "watch_error", "error": str(e)})

    def on_created(self, event):  # pragma: no cover - runtime behavior
        try:
            p = Path(getattr(event, "src_path", ""))
            if not p or not p.exists() or not p.is_file():
                return
            rp = p.resolve()
            # Route new docs file uploads
            if DOCS_DIR in rp.parents:
                auto_route_one(p)
                return
            # If a file appears directly under KB root (not in category folder), route it
            allowed = [KB_DIR / "core", KB_DIR / "expansion", KB_DIR / "agents", KB_DIR / "datasets", KB_DIR / "validation"]
            if KB_DIR in rp.parents and rp.parent == KB_DIR:
                auto_route_one(p)
        except Exception as e:
            _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "watch_route_error", "error": str(e)})


def watch(poll_interval_s: int = 5) -> None:
    """Start a watcher that keeps indexes in sync with file changes.

    Prefers watchdog if available; otherwise falls back to a simple polling loop.
    """
    _init_if_missing()
    _provenance_snapshot_once()

    if Observer is not None:  # watchdog path
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "watch_start", "impl": "watchdog"})
        handler = _OnChangeHandler()
        observer = Observer()
        observer.schedule(handler, str(KB_DIR), recursive=True)
        # Also watch docs for new uploads
        if DOCS_DIR.exists():
            observer.schedule(handler, str(DOCS_DIR), recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:  # pragma: no cover
            observer.stop()
        observer.join()
        return

    # Polling fallback
    _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "watch_start", "impl": "polling", "interval_s": poll_interval_s})
    last_hash = None
    try:
        while True:  # pragma: no cover - manual runtime behavior
            # Index knowledge base changes
            entries = sorted([_repo_rel(p) for p in KB_DIR.rglob("*") if p.exists()])
            cur_hash = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
            if cur_hash != last_hash:
                last_hash = cur_hash
                scan()
            # Route any new files under docs/
            if DOCS_DIR.exists():
                for p in DOCS_DIR.rglob("*"):
                    if p.is_file():
                        try:
                            auto_route_one(p)
                        except Exception as e:
                            _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "poll_route_error", "error": str(e), "file": _repo_rel(p)})
            time.sleep(max(1, int(poll_interval_s)))
    except KeyboardInterrupt:
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "watch_stop"})


# --------------- CLI ---------------

def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Knowledge Base Indexer")
    parser.add_argument("--scan", action="store_true", help="one-time scan/update of indexes")
    parser.add_argument("--rebuild", action="store_true", help="truncate index files and rebuild")
    parser.add_argument("--watch", action="store_true", help="watch knowledge_base and docs for changes; auto-route new docs")
    parser.add_argument("--poll", type=int, default=5, help="poll interval seconds for fallback watcher")
    parser.add_argument("--route", type=str, default=None, help="classify and route a single file path")
    parser.add_argument("--copy", action="store_true", help="copy instead of move when routing")
    parser.add_argument("--dry-run", action="store_true", help="show routing decision only; no changes")
    args = parser.parse_args(argv)

    _init_if_missing()

    if args.rebuild:
        # Truncate indexes to default scaffolds then scan
        for path, obj in (
            (CORE_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "items": []}),
            (EXPANSION_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "items": []}),
            (AGENTS_INDEX, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "agents": []}),
            (FEDERATION_MAP, {"version": "1.0", "generated_by": "utils/knowledge_indexer.py", "last_updated": None, "map": {}}),
        ):
            _atomic_write(path, _dump_yaml(obj))
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "rebuild_truncate"})
        res = scan()
        print(json.dumps(res, ensure_ascii=False))
        return 0

    if args.route:
        res = auto_route_one(args.route, copy=bool(args.copy), dry_run=bool(args.dry_run))
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if args.watch:
        watch(args.poll)
        return 0

    # Default: scan
    res = scan()
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli(sys.argv[1:]))


__all__ = [
    "scan",
    "refresh",
    "watch",
    "ensure_agent_kb_tree",
    "categorize_upload",
    "auto_route_one",
    "auto_routing",
]


# --------------- Classification & Auto-Routing ---------------

def _read_text_prefix(path: Path, max_bytes: int = 4096) -> str:
    try:
        with path.open("rb") as f:
            data = f.read(max_bytes)
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    except Exception:
        return ""


def _choose_category(name: str, snippet: str) -> tuple[str, float, str]:
    n = (name or "").lower()
    s = (snippet or "").lower()
    # Core heuristics
    core_kw = ["protocol", "handbook", "roadmap", "governance", "policy"]
    if any(k in n for k in core_kw) or any(k in s for k in core_kw):
        return "core", 0.97, "matched core keywords"
    # Agents heuristics
    if any(k in n for k in ["archivist", "genesis", "junie"]) or \
       "agents/" in n:
        return "agents", 0.9, "matched agent name"
    # Datasets heuristics
    if any(n.endswith(ext) for ext in [".csv", ".jsonl", ".parquet", ".tsv"]) or \
       any(k in n for k in ["dataset", "data_"]):
        return "datasets", 0.92, "dataset extension/keyword"
    # Validation heuristics
    if any(k in n for k in ["validation", "golden", "ground_truth", "test"]) or \
       any(k in s for k in ["expected", "assert", "ground truth"]):
        return "validation", 0.88, "validation signals"
    # Expansion default (whitepapers, research)
    if any(k in n for k in ["whitepaper", "research", "case_study", "spec"]) or \
       any(k in s for k in ["research", "study", "specification"]):
        return "expansion", 0.85, "research/spec indicators"
    # Fallback: expansion low confidence
    return "expansion", 0.6, "fallback"


def categorize_upload(path: Path, sample_bytes: int = 4096) -> dict:
    """Classify a document into one of: core, expansion, agents, datasets, validation.

    Returns standard envelope with category, confidence, and reason.
    """
    p = Path(path)
    snippet = _read_text_prefix(p, max_bytes=sample_bytes) if p.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".py"} else ""
    category, confidence, reason = _choose_category(p.name, snippet)
    return {
        "ok": True,
        "data": {"category": category, "confidence": float(confidence), "reason": reason},
        "error": None,
        "meta": {"ts": _now_iso(), "path": _repo_rel(p)},
    }


def _category_to_dir(category: str) -> Path:
    c = (category or "").lower()
    if c == "core":
        return KB_DIR / "core"
    if c == "agents":
        return KB_DIR / "agents"
    if c == "datasets":
        return KB_DIR / "datasets"
    if c == "validation":
        return KB_DIR / "validation"
    return KB_DIR / "expansion"


def _validate_destination(dst_dir: Path) -> None:
    allowed = [KB_DIR / "core", KB_DIR / "expansion", KB_DIR / "agents", KB_DIR / "datasets", KB_DIR / "validation"]
    resolve_path(str(dst_dir), base_dir=PROJECT_ROOT, allowed_roots=allowed)


def _append_backup_entry(original: Path, final: Path, sha256: str) -> None:
    _append_jsonl(BACKUP_LOG, {
        "ts": _now_iso(),
        "original_path": _repo_rel(original),
        "final_path": _repo_rel(final),
        "sha256": sha256,
    })


def _safe_collision_path(dst: Path, core_strict: bool = True) -> tuple[Path, bool]:
    """Return a non-conflicting path. If core_strict and exists, suffix the name."""
    if not dst.exists():
        return dst, False
    if core_strict:
        stem = dst.stem
        suffix = dst.suffix
        parent = dst.parent
        i = 1
        while True:
            trial = parent / f"{stem}_{i}{suffix}"
            if not trial.exists():
                return trial, True
            i += 1
    # Non-core may overwrite if allowed by caller; but we still suffix to be safe
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    i = 1
    while True:
        trial = parent / f"{stem}_{i}{suffix}"
        if not trial.exists():
            return trial, True
        i += 1


def _upsert_index_for_file(file_path: Path, status: str = "active") -> None:
    idx = _route_index_for_path(file_path)
    if idx is None:
        return
    obj = _load_yaml(idx) or {}
    # Agents index uses a different structure; only handle core/expansion here
    if idx in (CORE_INDEX, EXPANSION_INDEX):
        items = list(obj.get("items") or [])
        rec = {
            "id": hashlib.sha256(_repo_rel(file_path).encode("utf-8")).hexdigest()[:16],
            "title": _title_for_path(file_path),
            "path": _repo_rel(file_path),
            "version": "v1",
            "last_updated": _now_iso(),
            "indexed": True,
            "status": status,
            "sha256": _sha256_file(file_path),
        }
        items, _ = _upsert_item(items, rec, key="path")
        obj["items"] = sorted(items, key=lambda it: it.get("title", ""))
        obj["last_updated"] = _now_iso()
        _atomic_write(idx, _dump_yaml(obj))
    elif idx == AGENTS_INDEX:
        # Use existing helpers to refresh agents index
        try:
            # infer agent name from path: knowledge_base/agents/<name>/...
            parts = _repo_rel(file_path).split("/")
            if len(parts) >= 3:
                agent_name = parts[2]
                _update_agents_index(agent_name)
        except Exception:
            pass


def auto_route_one(path: str | Path, copy: bool = False, dry_run: bool = False) -> dict:
    """Classify and route a single file into knowledge_base/<category>/.

    - When copy=True, copy instead of moving (default False)
    - When dry_run=True, no changes are made; only a decision is returned
    """
    src = Path(path)
    if not src.exists() or not src.is_file():
        msg = f"source_not_found: {src}"
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "auto_route_error", "error": msg, "path": str(src)})
        return {"ok": False, "data": {}, "error": msg, "meta": {"ts": _now_iso()}}

    cat_res = categorize_upload(src)
    category = (cat_res.get("data") or {}).get("category") or "expansion"
    confidence = float((cat_res.get("data") or {}).get("confidence") or 0.0)
    dst_dir = _category_to_dir(category)
    _validate_destination(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst = dst_dir / src.name
    core_strict = (category == "core")
    dst_final, collided = _safe_collision_path(dst, core_strict=core_strict)

    # Core overwrite policy: collisions require approval (logged), we suffix instead of overwrite
    if core_strict and collided:
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "requires_approval", "reason": "core_collision_suffix", "original": _repo_rel(src), "planned": _repo_rel(dst), "final": _repo_rel(dst_final)})

    if dry_run:
        decision = {
            "ok": True,
            "data": {
                "category": category,
                "confidence": confidence,
                "original_path": _repo_rel(src),
                "final_path": _repo_rel(dst_final),
                "collided": bool(collided),
                "action": "copy" if copy else "move",
            },
            "error": None,
            "meta": {"ts": _now_iso()},
        }
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "auto_route_decision", **decision})
        return decision

    # Pre-hash
    sha_before = _sha256_file(src) or ""
    try:
        if copy:
            # Copy (binary-safe)
            data = src.read_bytes()
            dst_final.write_bytes(data)
        else:
            # Move
            src.replace(dst_final)
    except Exception as e:
        err = f"route_io_error: {e}"
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "auto_route_error", "error": err, "src": _repo_rel(src), "dst": _repo_rel(dst_final)})
        return {"ok": False, "data": {}, "error": str(e), "meta": {"ts": _now_iso()}}

    sha_after = _sha256_file(dst_final) or ""
    integrity_ok = (sha_before == sha_after) if sha_before else True

    # Backup record
    _append_backup_entry(src, dst_final, sha_after)

    # Update index
    try:
        _upsert_index_for_file(dst_final, status="active")
    except Exception as e:
        _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "index_update_error", "error": str(e), "file": _repo_rel(dst_final)})

    rec = {
        "ts": _now_iso(),
        "event": "auto_route",
        "original_path": _repo_rel(src),
        "final_path": _repo_rel(dst_final),
        "category": category,
        "confidence": confidence,
        "sha256_before": sha_before,
        "sha256_after": sha_after,
        "integrity_ok": integrity_ok,
    }
    _append_jsonl(TRACE_LOG, rec)

    return {
        "ok": True,
        "data": {
            "category": category,
            "confidence": confidence,
            "final_path": _repo_rel(dst_final),
            "integrity_ok": integrity_ok,
        },
        "error": None,
        "meta": {"ts": _now_iso()},
    }


# Convenience API: single-sweep auto routing

def auto_routing(once: bool = True, poll_interval_s: int = 5) -> dict:
    """Perform auto-routing for current docs/ (and KB root drops) once, or start watcher.

    When once=True (default):
      - Iterate docs/ files and call auto_route_one() on each
      - Iterate files directly under knowledge_base/ (root) and route them
      - Return counts and summary envelope
    When once=False:
      - Delegate to watch(poll_interval_s) for continuous routing
    """
    _init_if_missing()
    routed = 0
    errors = 0
    processed: list[str] = []
    # Route files under docs/
    if DOCS_DIR.exists():
        for p in DOCS_DIR.rglob("*"):
            if p.is_file():
                res = auto_route_one(p)
                processed.append(_repo_rel(p))
                if res.get("ok"):
                    routed += 1
                else:
                    errors += 1
    # Route files directly under KB root (not in a known category folder)
    if KB_DIR.exists():
        for p in KB_DIR.glob("*"):
            if p.is_file():
                res = auto_route_one(p)
                processed.append(_repo_rel(p))
                if res.get("ok"):
                    routed += 1
                else:
                    errors += 1
    payload = {"ok": errors == 0, "data": {"routed": routed, "errors": errors, "processed": processed}, "error": None if errors == 0 else "some_failures", "meta": {"ts": _now_iso()}}
    _append_jsonl(TRACE_LOG, {"ts": _now_iso(), "event": "auto_routing_sweep", **payload})
    if once:
        return payload
    # Continuous mode
    watch(poll_interval_s)
    return {"ok": True, "data": {"mode": "watch", "poll_interval_s": poll_interval_s}, "error": None, "meta": {"ts": _now_iso()}}
