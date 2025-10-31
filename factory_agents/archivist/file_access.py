import datetime
import json
from pathlib import Path

# Risk logger (optional)
try:
    from factory_agents.archivist import reasoning_core as _rc_risk
except Exception:
    _rc_risk = None  # type: ignore

# Dynamically locate the true project root (agent-factory)
FACTORY_ROOT = Path(__file__).resolve()
while FACTORY_ROOT.name != "agent-factory" and FACTORY_ROOT.parent != FACTORY_ROOT:
    FACTORY_ROOT = FACTORY_ROOT.parent

print(f"[Archy Config] 🧭 Factory root detected: {FACTORY_ROOT}")

# === Access scope & protection (Phase 1: restrict to specific subdirs) ===
ALLOWED_ROOTS = [
    FACTORY_ROOT / "factory_agents",
    FACTORY_ROOT / "knowledge_base",
    FACTORY_ROOT / "registry",
    FACTORY_ROOT / "docs",
    FACTORY_ROOT / "logs",
]
PROTECTED_PATTERNS = [".env", ".git", "secrets", "api_keys", "config/api_keys", "factory_config/api_keys"]


def is_within_factory(path: Path) -> bool:
    """Return True if the path is inside one of the allowed roots under the project root."""
    for root in ALLOWED_ROOTS:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _audit(event: str, path: Path | str, status: str):
    ts = datetime.datetime.now().isoformat()
    log_file = FACTORY_ROOT / "logs" / "file_access_audit.log"
    try:
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {event}: {path} -> {status}\n")
        # Risk hook (Low for reads/lists, Medium for writes)
        if _rc_risk is not None:
            try:
                _rc_risk.risk_assess(event.lower(), str(path))
            except Exception:
                pass
    except Exception:
        # Best-effort logging
        pass


# === Helper: pending overwrite buffer ===
BUFFER_FILE = FACTORY_ROOT / "logs" / "overwrite_buffer.json"

def _load_buffer() -> dict:
    try:
        if BUFFER_FILE.exists():
            return json.loads(BUFFER_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_buffer(data: dict) -> None:
    try:
        BUFFER_FILE.parent.mkdir(exist_ok=True)
        BUFFER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


# === Directory listing ===

def list_dir(relative_path: str | None = None) -> dict:
    """Safely list directories/files within project root.
    If relative_path is None, returns top-level entries of the project root.
    """
    try:
        if relative_path is None or relative_path.strip() == "":
            # Show only allowed roots for clarity at top-level
            items = []
            for root in ALLOWED_ROOTS:
                if root.exists():
                    items.append({"name": str(root.relative_to(FACTORY_ROOT)), "type": "dir"})
            _audit("LIST", "<root>", "Success")
            return {"status": "success", "path": str(FACTORY_ROOT), "items": items}

        target = (FACTORY_ROOT / relative_path).resolve()
        if not is_within_factory(target):
            _audit("LIST", target, "Denied")
            return {"status": "error", "error": "Path outside project root.", "path": str(target)}
        if not target.exists():
            _audit("LIST", target, "NotFound")
            return {"status": "error", "error": "Path does not exist", "path": str(target)}
        if not target.is_dir():
            _audit("LIST", target, "NotDirectory")
            return {"status": "error", "error": "Not a directory", "path": str(target)}
        items = []
        for p in sorted(target.iterdir()):
            items.append({"name": p.name, "type": "dir" if p.is_dir() else "file"})
        _audit("LIST", target, "Success")
        return {"status": "success", "path": str(target), "items": items}
    except Exception as e:
        _audit("LIST", relative_path or "<none>", f"Error {e}")
        return {"status": "error", "error": str(e), "path": relative_path or ""}


# === Read / Write operations ===

def safe_read(relative_path: str) -> dict:
    target = (FACTORY_ROOT / relative_path).resolve()
    if not is_within_factory(target):
        _audit("READ", target, "Denied")
        return {"status": "error", "error": "Access outside project root denied.", "path": str(target)}
    try:
        content = target.read_text(encoding="utf-8")
        _audit("READ", target, "Success")
        return {"status": "success", "content": content, "path": str(target)}
    except FileNotFoundError:
        _audit("READ", target, "NotFound")
        return {"status": "error", "error": "File does not exist", "path": str(target)}
    except Exception as e:
        _audit("READ", target, f"Error {e}")
        return {"status": "error", "error": str(e), "path": str(target)}


def safe_write(relative_path: str, content: str, confirm: bool = False) -> dict:
    target = (FACTORY_ROOT / relative_path).resolve()
    if not is_within_factory(target):
        _audit("WRITE", target, "Denied")
        return {"status": "error", "error": "Write outside project root denied.", "path": str(target)}
    # protect sensitive files/dirs
    if any(pat in str(target) for pat in PROTECTED_PATTERNS):
        _audit("WRITE", target, "ProtectedDenied")
        return {"status": "error", "error": "Write denied: protected file", "path": str(target)}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not confirm:
            # buffer the attempted content for confirmation
            buf = _load_buffer()
            buf[str(target)] = content
            _save_buffer(buf)
            _audit("WRITE", target, "AwaitingConfirmation")
            return {
                "status": "requires_confirmation",
                "message": f"⚠️ File already exists. Confirm overwrite with 'confirm overwrite {relative_path}'",
                "path": str(target)
            }

        # Use buffered content if available and no new content supplied
        if confirm:
            buf = _load_buffer()
            buffered = buf.pop(str(target), None)
            if buffered is not None and (content is None or content == ""):
                content = buffered
            _save_buffer(buf)

        target.write_text(content, encoding="utf-8")
        _audit("WRITE", target, "Success")
        return {"status": "success", "path": str(target)}

    except Exception as e:
        _audit("WRITE", target, f"Error {e}")
        return {"status": "error", "error": str(e), "path": str(target)}


def governed_write(relative_path: str, content: str, author: str = "Archy", reason: str = "Routine") -> dict:
    """Write content under governance control and audit header."""
    header = (
        f"# ======================================================\n"
        f"# Governed Write Operation\n"
        f"# Author: {author}\n"
        f"# Reason: {reason}\n"
        f"# Path: {relative_path}\n"
        f"# ======================================================\n\n"
    )
    result = safe_write(relative_path, header + content)
    _audit("GOVERNED_WRITE", relative_path, result.get("status", "unknown"))
    return result
