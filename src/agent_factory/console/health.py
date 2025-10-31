from __future__ import annotations

import csv
import os
from typing import List, Dict, Any

from fastapi import APIRouter

router = APIRouter()


def _read_last_health_rows(path: str, limit: int = 100) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for r in reader:
                if not r:
                    continue
                try:
                    rows.append({
                        "timestamp": r[0] if len(r) > 0 else "",
                        "port": r[1] if len(r) > 1 else "",
                        "status": r[2] if len(r) > 2 else "",
                        "mode": r[3] if len(r) > 3 else "",
                    })
                except Exception:
                    # skip malformed line
                    continue
    except Exception:
        return []
    return rows[-limit:]


@router.get("/health/genesis")
def get_genesis_health() -> Dict[str, Any]:
    path = os.path.join("compliance", "audit_log", "genesis_health.csv")
    data = _read_last_health_rows(path, limit=100)
    return {"ok": bool(data), "data": data}
