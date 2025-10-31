from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from agent_factory.utils.paths import PROJECT_ROOT, resolve_path
from agent_factory.services.audit.audit_logger import log_event

# Allowed extensions for both read and write
ALLOWED_EXTENSIONS = {".yaml", ".yml", ".json", ".md", ".txt"}

# Whitelisted roots for SAFE READ operations
ALLOWED_READ_ROOTS = [
    PROJECT_ROOT / "factory_governance",
    PROJECT_ROOT / "knowledge_base",
    PROJECT_ROOT / "registry",
    PROJECT_ROOT / "docs",
]

# Whitelisted roots for GOVERNED WRITE operations (least privilege)
ALLOWED_WRITE_ROOTS = [
    PROJECT_ROOT / "knowledge_base" / "curated",
    PROJECT_ROOT / "knowledge_base" / "conversations",
]

# Explicitly restricted write roots
RESTRICTED_WRITE_ROOTS = [
    PROJECT_ROOT / "factory_governance",
    PROJECT_ROOT / "personas",
]


def _ext_ok(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def _under(root: Path, path: Path) -> bool:
    root_s = str(root.resolve())
    path_s = str(path.resolve())
    return path_s.startswith(root_s)


def safe_read(file_path: str) -> Dict[str, object]:
    """Safely read a text-like file from whitelisted directories.

    Returns a structured dict with status, path, and content or error.
    """
    try:
        resolved = resolve_path(file_path, base_dir=PROJECT_ROOT, allowed_roots=ALLOWED_READ_ROOTS)
        if not _ext_ok(resolved):
            raise ValueError(f"Extension not allowed: {resolved.suffix}")
        data = resolved.read_text(encoding="utf-8")
        event = log_event("file_read", {"path": str(resolved), "ok": True})
        logging.info(json.dumps({"action": "file_read", "path": str(resolved), "trace": event["meta"]["trace_id"]}))
        return {"status": "success", "path": str(resolved), "content": data}
    except Exception as e:
        log_event("file_read_error", {"requested": file_path, "error": str(e)})
        logging.exception(f"safe_read failed: {file_path}")
        return {"status": "error", "error": str(e)}


def governed_write(file_path: str, content: str, actor: Optional[str] = None) -> Dict[str, object]:
    """Write a file under governance controls.

    - Only allows writing under ALLOWED_WRITE_ROOTS
    - Disallows writes into governance/personas
    - Respects HITL gate via env HITL_APPROVE (true/false)
    """
    actor = actor or os.getenv("ARCHY_ACTOR", "Archy")
    try:
        # Enforce allowed write roots
        resolved = resolve_path(file_path, base_dir=PROJECT_ROOT, allowed_roots=ALLOWED_WRITE_ROOTS)

        # Hard-restrict certain roots regardless
        for restricted in RESTRICTED_WRITE_ROOTS:
            if _under(restricted, resolved):
                raise PermissionError(f"Write access restricted for: {restricted}")

        if not _ext_ok(resolved):
            raise ValueError(f"Extension not allowed: {resolved.suffix}")

        # HITL placeholder
        if os.getenv("HITL_APPROVE", "false").lower() != "true":
            log_event("file_write_hitl_required", {"actor": actor, "path": str(resolved)})
            return {
                "status": "pending_approval",
                "error": "HITL approval required. Set HITL_APPROVE=true to proceed.",
                "path": str(resolved),
            }

        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)

        evt = log_event("file_write", {"actor": actor, "path": str(resolved), "bytes": len(content)})
        logging.info(json.dumps({"action": "file_write", "path": str(resolved), "actor": actor, "trace": evt["meta"]["trace_id"]}))
        return {"status": "success", "path": str(resolved)}
    except Exception as e:
        log_event("file_write_error", {"actor": actor, "requested": file_path, "error": str(e)})
        logging.exception(f"governed_write failed: {file_path}")
        return {"status": "error", "error": str(e)}


def list_dir(path: Optional[str] = None, max_entries: int = 200) -> Dict[str, object]:
    """List directory contents within whitelisted read roots.

    If path is None, returns the allowed root directories.
    """
    try:
        if not path:
            roots = [str(p) for p in ALLOWED_READ_ROOTS]
            log_event("list_roots", {"roots": roots})
            return {"status": "success", "roots": roots}

        resolved = resolve_path(path, base_dir=PROJECT_ROOT, allowed_roots=ALLOWED_READ_ROOTS)
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
        if resolved.is_file():
            raise IsADirectoryError(f"Not a directory: {resolved}")

        items = []
        for child in sorted(resolved.iterdir()):
            if child.is_dir():
                items.append({"name": child.name, "type": "dir"})
            else:
                # Only list files with allowed extensions
                if _ext_ok(child):
                    items.append({"name": child.name, "type": "file"})
            if len(items) >= max_entries:
                break
        log_event("list_dir", {"path": str(resolved), "count": len(items)})
        return {"status": "success", "path": str(resolved), "items": items}
    except Exception as e:
        log_event("list_dir_error", {"requested": path, "error": str(e)})
        logging.exception(f"list_dir failed: {path}")
        return {"status": "error", "error": str(e)}


__all__ = [
    "safe_read",
    "governed_write",
    "list_dir",
]
