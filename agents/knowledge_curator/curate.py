from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import sys

# Ensure repo-root and src are on sys.path
import tools.startup  # noqa: F401

# Prefer centralized config loader; fallback to dotenv below
try:
    from tools.config_loader import load_env  # type: ignore
    load_env()
except Exception:
    pass

from agent_factory.services.audit.audit_logger import log_knowledge_ingest
from agent_factory.utils.procedural_memory_pg import insert_ingest
from agent_factory.utils.paths import KB_SRC_DIR, PROVENANCE_DIR
from agent_factory.services.memory.engine import MemoryEngine


def _load_text(file_path: Path) -> list[str]:
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except Exception:
        return []
    # simple line-based chunking (non-empty lines grouped by 50)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    for i, ln in enumerate(lines, 1):
        buf.append(ln)
        if len(buf) >= 50:
            chunks.append("\n".join(buf))
            buf = []
    if buf:
        chunks.append("\n".join(buf))
    return chunks or ([text] if text else [])


def _load_csv(file_path: Path) -> list[str]:
    try:
        import csv
        rows = []
        with file_path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                rows.append(",".join(row))
        # chunk rows by 100
        chunks: list[str] = []
        for i in range(0, len(rows), 100):
            chunks.append("\n".join(rows[i:i+100]))
        return chunks or (["\n".join(rows)] if rows else [])
    except Exception:
        return []


def _load_pdf(file_path: Path) -> list[str]:
    # Try PyPDF2 as fallback; if not available, return single placeholder chunk
    try:
        from langchain_community.document_loaders import PyPDFLoader  # type: ignore
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()
        return [d.page_content for d in docs if getattr(d, "page_content", None)]
    except Exception:
        try:
            import PyPDF2  # type: ignore
            pages: list[str] = []
            with open(file_path, "rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                for p in reader.pages:
                    try:
                        pages.append(p.extract_text() or "")
                    except Exception:
                        pages.append("")
            return [p for p in pages if p]
        except Exception:
            return [f"PDF:{file_path.name}"]


def curate(source_path: Optional[str] = None, curator: Optional[str] = None) -> None:
    """Knowledge Curator 2.0: multi-format ingestion with provenance.

    - Auto-detects .txt, .md, .pdf, .csv
    - Uses lightweight loaders (with graceful fallbacks)
    - Writes provenance JSON per file
    - Logs knowledge_ingest and inserts memory via MemoryEngine
    """
    load_dotenv()
    if source_path:
        path = Path(source_path)
    else:
        path = KB_SRC_DIR

    # Collect candidate files
    if path.is_dir():
        files = (
            list(path.rglob("*.md"))
            + list(path.rglob("*.txt"))
            + list(path.rglob("*.pdf"))
            + list(path.rglob("*.csv"))
        )
    else:
        files = [path]

    engine = MemoryEngine()
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    for f in files:
        suffix = f.suffix.lower()
        if suffix in {".md", ".txt"}:
            chunks = _load_text(f)
        elif suffix == ".csv":
            chunks = _load_csv(f)
        elif suffix == ".pdf":
            chunks = _load_pdf(f)
        else:
            chunks = _load_text(f)

        # Insert to memory engine (content-only for stubs)
        if chunks:
            engine.add_documents(chunks, metadata={"source": str(f)})

        # Audit + DB record (existing helpers)
        log_knowledge_ingest(f.name, len(chunks))
        insert_ingest(source_path=f, vector_count=len(chunks), curator=curator)

        # Provenance JSON
        try:
            import json
            from datetime import datetime, timezone
            prov = {
                "source": str(f),
                "chunks": len(chunks),
                "curator": curator or "auto",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            file_id = f.stem
            (PROVENANCE_DIR / f"{file_id}.json").write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        total_chunks += len(chunks)

    print(f"Curated {len(files)} files, approx chunks: {total_chunks}")


if __name__ == "__main__":
    # Allow CLI: python agents/knowledge_curator/curate.py <path?> <curator?>
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    arg_curator = sys.argv[2] if len(sys.argv) > 2 else None
    curate(source_path=arg_path, curator=arg_curator)
