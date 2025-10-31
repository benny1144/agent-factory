from __future__ import annotations
from pathlib import Path
import json

def aggregate_audits(logs_dir: str | Path) -> dict:
    return {'ok': True, 'data': {'audits': 0}}
