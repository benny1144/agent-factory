from __future__ import annotations

"""Orion Control Plane Entrypoint (Phase 39.0)

Starts the Orion control plane which periodically audits the repository
structure and monitors governance drift. This process also announces
online status to the Watchtower chat log and can be supervised by the
Watchtower UI.
"""

from pathlib import Path

try:
    from .control_plane import OrionControlPlane  # package-relative import
except Exception:  # pragma: no cover
    # Fallback to allow running as a script if package import fails
    import importlib.util as _ilu
    _here = Path(__file__).resolve()
    _cp = _here.parent / "control_plane.py"
    spec = _ilu.spec_from_file_location("orion_control_plane", str(_cp))
    mod = _ilu.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    OrionControlPlane = getattr(mod, "OrionControlPlane")  # type: ignore


def main() -> int:
    orion = OrionControlPlane()
    orion.initialize()
    orion.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
