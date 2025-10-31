from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

# Repo root resolution
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
CENTRAL_ENV_FILE = CONFIG_DIR / ".env"


def load_env(path: Optional[str | os.PathLike[str]] = None, override: bool = False) -> None:
    """Load environment variables from a centralized location.

    Order of precedence:
    1. Explicit path argument (if provided)
    2. config/.env (preferred)
    3. .env at repo root (backward compatibility)

    Args:
        path: Optional explicit path to an env file
        override: If True, environment variables from file override existing process env
    """
    if load_dotenv is None:
        return

    # Prefer explicit path
    if path:
        p = Path(path)
        if p.exists():
            load_dotenv(p, override=override)
            return

    # Prefer centralized config/.env
    if CENTRAL_ENV_FILE.exists():
        load_dotenv(CENTRAL_ENV_FILE, override=override)
        return

    # Fallback to legacy .env in repo root
    if DEFAULT_ENV_FILE.exists():
        load_dotenv(DEFAULT_ENV_FILE, override=override)
        return


def require_flag(env_name: str, default: str | None = None) -> bool:
    """Return boolean for an env flag (case-insensitive "true")."""
    val = os.getenv(env_name, default or "false")
    return str(val).lower() == "true"


__all__ = ["load_env", "require_flag", "PROJECT_ROOT", "CONFIG_DIR", "CENTRAL_ENV_FILE"]
