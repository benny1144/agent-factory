import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import TypedDict, Union, Any
from crewai.tools import tool

# Load .env if present (safe if already loaded)
_dotenv = find_dotenv(filename=".env", usecwd=True)
if _dotenv:
    load_dotenv(_dotenv, override=False)

# Ensure GOOGLE_API_KEY is set even if only GEMINI_API_KEY is provided
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss_index"

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
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        db = FAISS.load_local(str(VECTOR_STORE_PATH), embeddings, allow_dangerous_deserialization=True)
        
        # Perform a similarity search
        results = db.similarity_search(query, k=3)  # Get top 3 most relevant chunks
        
        if not results:
            return {"success": True, "result": "No relevant information found in the knowledge base for that query."}
            
        # Combine the content of the relevant chunks
        retrieved_knowledge = "\n---\n".join([doc.page_content for doc in results])
        
        return {"success": True, "result": retrieved_knowledge}

    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred while searching the knowledge base: {e}"}
#
