from __future__ import annotations
import json, tarfile, io
from pathlib import Path

SCHEMA = {'metadata': {}, 'dependencies': [], 'state': {}}

def export_agent(src_dir: str | Path, out_path: str | Path) -> str:
    src = Path(src_dir); out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, 'w:gz') as tar:
        for p in src.rglob('*'):
            tar.add(p, arcname=p.relative_to(src))
    return str(out)

def import_agent(pkg_path: str | Path, dest_dir: str | Path) -> str:
    pkg = Path(pkg_path); dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(pkg, 'r:gz') as tar:
        tar.extractall(dest)
    return str(dest)
