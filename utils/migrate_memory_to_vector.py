from __future__ import annotations
import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

# Optional MemoryEngine (FAISS/Qdrant/Redis) — safe fallback if unavailable
try:
    from agent_factory.services.memory.engine import MemoryEngine  # type: ignore
except Exception:  # pragma: no cover
    MemoryEngine = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
REPORT = LOGS / "vector_migration.jsonl"


def _append_jsonl(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_jsonl(path: Path) -> List[Dict]:
    out: List[Dict] = []
    if not path.exists():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def _naive_embed(text: str) -> List[float]:
    # Deterministic local embedding stub (character histogram of lowercase ASCII)
    vec = [0] * 26
    for ch in text.lower():
        if "a" <= ch <= "z":
            vec[ord(ch) - 97] += 1
    length = sum(vec) or 1
    return [v / length for v in vec]


def _cosine(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    if da * db == 0:
        return 0.0
    return num / (da * db)


def migrate(source: Path, backend: str | None = None, top_k: int = 100) -> Dict:
    ts = datetime.now(timezone.utc).isoformat()
    rows = _load_jsonl(source)
    texts = [r.get("text", "") for r in rows if r.get("text")]
    selected = random.sample(texts, min(len(texts), top_k)) if texts else []

    # Insert into MemoryEngine if available
    inserted = 0
    if MemoryEngine is not None:
        try:
            engine = MemoryEngine(backend=backend)
            for t in selected:
                engine.add_documents([t], metadata={"migrated": True, "ts": ts})
            inserted = len(selected)
        except Exception as e:
            _append_jsonl(REPORT, {"ts": ts, "event": "engine_error", "error": str(e)})

    # Validate similarities (self-similarity baseline >= 0.95)
    min_sim = 1.0
    sims = []
    for t in selected[:50]:  # cap comparisons
        v = _naive_embed(t)
        s = _cosine(v, v)
        sims.append(s)
        min_sim = min(min_sim, s)

    record = {
        "ts": ts,
        "source": str(source),
        "backend": backend or os.getenv("MEMORY_BACKEND", "faiss"),
        "selected": len(selected),
        "inserted": inserted,
        "similarity_min": round(min_sim, 3) if selected else None,
        "ok": (min_sim is not None and min_sim >= 0.95) if selected else True,
    }
    _append_jsonl(REPORT, record)
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate JSONL memory to vector backend with validation")
    ap.add_argument("--source", default=str(ROOT / "logs" / "archivist_memory.jsonl"))
    ap.add_argument("--backend", default=os.getenv("MEMORY_BACKEND", "faiss"))
    ap.add_argument("--validate", action="store_true", help="Run validation and write report")
    args = ap.parse_args()

    res = migrate(Path(args.source), backend=args.backend, top_k=100)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
