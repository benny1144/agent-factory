import os
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from typing import TypedDict, Union, Any
from crewai.tools import tool

# Optional FAISS + embeddings imports guarded for environments without these deps
try:
    from langchain_community.vectorstores import FAISS  # type: ignore
    from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    FAISS = None  # type: ignore
    GoogleGenerativeAIEmbeddings = None  # type: ignore

# Load .env if present (safe if already loaded)
_dotenv = find_dotenv(filename=".env", usecwd=True)
if _dotenv:
    load_dotenv(_dotenv, override=False)

# Ensure GOOGLE_API_KEY is set even if only GEMINI_API_KEY is provided
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss_index"
MANIFEST_PATH = VECTOR_STORE_PATH / "manifest.json"

class SuccessResponse(TypedDict):
    """Standardized success response envelope."""
    success: bool
    result: Any

class ErrorResponse(TypedDict):
    """Standardized error response envelope."""
    success: bool
    error: str

ToolResponse = Union[SuccessResponse, ErrorResponse]

@tool("Knowledge Base Search")
def search_knowledge_base(query: str) -> ToolResponse:
    """
    Searches the Agent Factory's knowledge base to find relevant information.

    Use this tool to retrieve best practices, architectural patterns, and
    project principles before designing any new agent crew.

    Args:
        query: The specific question or topic to search for in the knowledge base.

    Returns:
        A dictionary indicating success or failure:
        - On success: `{"success": true, "result": "The retrieved information..."}`
        - On failure: `{"success": false, "error": "error message"}`
    """
    try:
        if FAISS is None or GoogleGenerativeAIEmbeddings is None:
            # Deterministic stub when deps are missing
            return {"success": True, "result": "[stub] Vector search unavailable; install langchain_community + google-genai to enable."}
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        db = FAISS.load_local(str(VECTOR_STORE_PATH), embeddings, allow_dangerous_deserialization=True)
        results = db.similarity_search(query, k=3)
        if not results:
            return {"success": True, "result": "No relevant information found in the knowledge base for that query."}
        retrieved_knowledge = "\n---\n".join([doc.page_content for doc in results])
        return {"success": True, "result": retrieved_knowledge}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred while searching the knowledge base: {e}"}


def rebuild_vector_index() -> dict:
    """Best-effort vector index rebuild (stub).

    For now, writes/updates a manifest.json with timestamp to serve as an index state artifact.
    """
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    payload = {"updated": __import__("datetime").datetime.utcnow().isoformat() + "Z", "note": "CLI reindex stub"}
    try:
        MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {"ok": True, "path": str(MANIFEST_PATH)}


def manifest_status() -> dict:
    """Return status of the FAISS index manifest for sanity checks.

    Returns a JSON dict with keys: exists, path, size_bytes, mtime.
    """
    info = {
        "exists": MANIFEST_PATH.exists(),
        "path": str(MANIFEST_PATH),
        "size_bytes": None,
        "mtime": None,
    }
    try:
        if MANIFEST_PATH.exists():
            stat = MANIFEST_PATH.stat()
            info["size_bytes"] = stat.st_size
            from datetime import datetime
            info["mtime"] = datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"
    except Exception:
        pass
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Charter tools CLI")
    parser.add_argument("--reindex", action="store_true", help="Rebuild or refresh the vector index (stub)")
    parser.add_argument("--sync-governance", action="store_true", help="Emit a governance sync note (stdout only)")
    parser.add_argument("--status", action="store_true", help="Print JSON with vector index manifest status")
    args = parser.parse_args()

    if args.reindex:
        res = rebuild_vector_index()
        print(json.dumps(res))
    if args.sync_governance:
        print(json.dumps({"ok": True, "event": "sync-governance"}))
    if args.status:
        print(json.dumps(manifest_status(), ensure_ascii=False))


if __name__ == "__main__":
    main()
