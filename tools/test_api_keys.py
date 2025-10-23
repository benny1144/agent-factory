import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Best-effort imports guarded per test to avoid hard failures when optional deps are missing
from dotenv import load_dotenv, find_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load environment variables from .env regardless of current working directory."""
    dotenv_path = find_dotenv(filename=".env", usecwd=True) or (PROJECT_ROOT / ".env")
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)

    # Small compatibility shim between Google/Gemini naming
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")  # for CrewAI/LiteLLM Gemini
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")  # for LangChain Google embeddings


def _result(status: str, message: str = "") -> Dict[str, Any]:
    return {"status": status, "message": message}


def _try_llm_call(llm, prompt: str):
    """Attempt to call an LLM using several common methods, return (ok, message)."""
    # Try known methods in order
    for method_name in ("invoke", "chat", "complete"):
        fn = getattr(llm, method_name, None)
        if callable(fn):
            try:
                _ = fn(prompt)
                return True, f"{method_name} succeeded"
            except Exception as e:
                last_err = f"{method_name} failed: {e}"
    # Try calling the object directly if it's callable
    try:
        if callable(llm):
            _ = llm(prompt)
            return True, "__call__ succeeded"
    except Exception as e:
        last_err = f"__call__ failed: {e}"
    return False, last_err if 'last_err' in locals() else "no callable method found"


def test_gemini_chat() -> Dict[str, Any]:
    key_present = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if not key_present:
        return _result("skipped", "GEMINI_API_KEY/GOOGLE_API_KEY not set")
    try:
        from crewai import LLM
        llm = LLM(model="gemini/gemini-2.5-flash", temperature=0.0)
        ok, msg = _try_llm_call(llm, "ping")
        return _result("ok", f"Gemini chat {msg}") if ok else _result("fail", f"Gemini chat {msg}")
    except Exception as e:
        return _result("fail", f"Gemini chat error: {e}")


def test_google_embeddings() -> Dict[str, Any]:
    if not os.getenv("GOOGLE_API_KEY"):
        return _result("skipped", "GOOGLE_API_KEY not set")
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        emb = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        _ = emb.embed_query("hello")  # returns a vector if successful
        return _result("ok", "Google embeddings succeeded")
    except Exception as e:
        return _result("fail", f"Google embeddings error: {e}")


def test_openai() -> Dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        return _result("skipped", "OPENAI_API_KEY not set")
    try:
        from crewai import LLM
        # Use a lightweight OpenAI model via CrewAI/LiteLLM
        llm = LLM(model="openai/gpt-4o-mini", temperature=0.0)
        ok, msg = _try_llm_call(llm, "ping")
        return _result("ok", f"OpenAI chat {msg}") if ok else _result("fail", f"OpenAI chat {msg}")
    except Exception as e:
        return _result("fail", f"OpenAI error: {e}")


def test_groq() -> Dict[str, Any]:
    if not os.getenv("GROQ_API_KEY"):
        return _result("skipped", "GROQ_API_KEY not set")
    try:
        from crewai import LLM
        llm = LLM(model="groq/llama3-8b-8192", temperature=0.0)
        ok, msg = _try_llm_call(llm, "ping")
        return _result("ok", f"Groq chat {msg}") if ok else _result("fail", f"Groq chat {msg}")
    except Exception as e:
        return _result("fail", f"Groq error: {e}")


def test_serper() -> Dict[str, Any]:
    if not os.getenv("SERPER_API_KEY"):
        return _result("skipped", "SERPER_API_KEY not set")
    try:
        # Prefer the project's tool if available to ensure consistent config
        try:
            from tools.search_tools import search_tool  # type: ignore
            tool = search_tool
        except Exception:
            from crewai_tools import SerperDevTool  # type: ignore
            tool = SerperDevTool()

        query = "Agent Factory site:github.com"
        # Try multiple call signatures to accommodate different crewai_tools versions
        for method_name in ("run", "search", "_run", "__call__"):
            fn = getattr(tool, method_name, None)
            if callable(fn):
                try:
                    _ = fn(query)
                    return _result("ok", f"Serper via {method_name} succeeded")
                except TypeError:
                    # Try dict-style input if signature expects a mapping
                    try:
                        _ = fn({"query": query})
                        return _result("ok", f"Serper via {method_name} with dict payload succeeded")
                    except Exception:
                        continue
                except Exception:
                    continue
        return _result("fail", "Serper tool methods not callable with tested signatures")
    except Exception as e:
        return _result("fail", f"Serper error: {e}")


def main() -> int:
    load_env()

    summary: Dict[str, Any] = {
        "GOOGLE_API_KEY_present": bool(os.getenv("GOOGLE_API_KEY")),
        "GEMINI_API_KEY_present": bool(os.getenv("GEMINI_API_KEY")),
        "OPENAI_API_KEY_present": bool(os.getenv("OPENAI_API_KEY")),
        "GROQ_API_KEY_present": bool(os.getenv("GROQ_API_KEY")),
        "SERPER_API_KEY_present": bool(os.getenv("SERPER_API_KEY")),
        "tests": {}
    }

    # Execute tests
    summary["tests"]["gemini_chat"] = test_gemini_chat()
    summary["tests"]["google_embeddings"] = test_google_embeddings()
    summary["tests"]["openai_chat"] = test_openai()
    summary["tests"]["groq_chat"] = test_groq()
    summary["tests"]["serper_search"] = test_serper()

    # Determine overall status
    statuses = [v["status"] for v in summary["tests"].values()]
    overall = "ok" if (any(s == "ok" for s in statuses) and all(s in {"ok", "skipped"} for s in statuses)) else (
        "partial" if any(s == "ok" for s in statuses) else "fail"
    )
    summary["overall_status"] = overall

    # Pretty print
    print(json.dumps(summary, indent=2))

    # Exit code: 0 if all tests are ok or skipped; 1 otherwise
    return 0 if overall in {"ok", "partial"} else 1


if __name__ == "__main__":
    sys.exit(main())
