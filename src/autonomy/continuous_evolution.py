from __future__ import annotations
from typing import List
def redundancy_filter(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x); seen.add(x)
    return out
