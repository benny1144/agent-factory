import os
from openai import OpenAI
from dotenv import load_dotenv
from factory_agents.archivist.file_access import safe_read, safe_write


# Standardized ChatGPT Model Suite only (OpenAI)
# Gemini/Groq paths removed per Phase 38.5 model standardization.

# === Auto-load API keys ===
def ensure_key(env_name: str, fallback_prefix: str = "factory_config/api_keys.env"):
    """Ensure that a given API key is available in the environment."""
    if not os.getenv(env_name):
        try:
            with open(fallback_prefix, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(f"{env_name}="):
                        os.environ[env_name] = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            print(f"[WARN] Missing API key file: {fallback_prefix}")


# ✅ Load .env if present
load_dotenv("factory_config/api_keys.env")

# ✅ Ensure OpenAI key exists (others optional)
for key in [
    "OPENAI_API_KEY",
    "ARXIV_KEY",
    "SEMANTIC_KEY",
    "SERPER_API_KEY",
]:
    ensure_key(key)

# === Initialize OpenAI client ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model names configurable via env; defaults per standard stack
OPENAI_MODEL_REFLECTIVE = os.getenv("OPENAI_MODEL_REFLECTIVE", "gpt-4o-mini")
OPENAI_MODEL_ETHICS = os.getenv("OPENAI_MODEL_ETHICS", "gpt-4-turbo")
OPENAI_MODEL_SUMMARY = os.getenv("OPENAI_MODEL_SUMMARY", "gpt-4o")

print("[INIT] OpenAI client ready; standardized models configured.")

import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
LOGS_DIR.mkdir(exist_ok=True)
REASONING_LOG = LOGS_DIR / "archy_reasoning.log"


def log_reasoning(engine: str, prompt: str, response: str):
    """Log reasoning events for audit and traceability."""
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    with open(REASONING_LOG, "a", encoding="utf-8") as f:
        f.write(
            f"[{ts}] Engine: {engine}\n"
            f"Prompt: {prompt[:200].replace(chr(10), ' ')}\n"
            f"Response: {response[:200].replace(chr(10), ' ')}\n"
            f"{'-'*80}\n"
        )


def think(prompt: str) -> str:
    """
    Archy's standardized reasoning core (OpenAI-only) with audit logging.
    Uses environment-configured models per Phase 38.5.
    """
    try:
        if client and os.getenv("OPENAI_API_KEY"):
            response = client.chat.completions.create(
                model=OPENAI_MODEL_REFLECTIVE,
                messages=[
                    {"role": "system", "content": "You are Archy, the Archivist of the Agent Factory."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            result = (response.choices[0].message.content or "").strip()
            log_reasoning(f"OpenAI {OPENAI_MODEL_REFLECTIVE}", prompt, result)
            return result
        # Fallback (no OpenAI configured)
        result = "[ReasoningError] No valid reasoning engine available."
        log_reasoning("Fallback", prompt, result)
        return result
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:200]} (trace redacted)"
        log_reasoning("Exception", prompt, f"[ReasoningError] {err}")
        return f"[ReasoningError] {err}"

import statistics

def reflect_on_reasoning(log_path: Path = REASONING_LOG, recent_n: int = 10) -> str:
    """
    Archy self-audits her recent reasoning sessions for coherence, clarity, and bias signals.
    Uses the most recent N log entries to generate a meta-analysis summary.
    """

    if not log_path.exists():
        return "[Reflection] No reasoning logs found to analyze."

    try:
        # Read last N reasoning entries
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Group entries by separator
        blocks, current = [], []
        for line in lines:
            if line.startswith("--------"):
                if current:
                    blocks.append("".join(current))
                    current = []
            else:
                current.append(line)
        if current:
            blocks.append("".join(current))

        recent_entries = blocks[-recent_n:]
        joined_logs = "\n".join(recent_entries)

        # Ask Archy to analyze her own log
        audit_prompt = f"""
You are Archy, the self-reflective Archivist of the Agent Factory.

Analyze the following reasoning log entries from your past sessions.
For each, infer:
- Clarity (1–10)
- Coherence (1–10)
- Signs of bias or factual drift
- Any patterns in reasoning quality

Then produce a brief meta-summary of your recent performance
and suggest one improvement to enhance future reasoning.

LOG SAMPLE:
{joined_logs}
        """.strip()

        result = think(audit_prompt)

        # Log the reflection result
        reflection_log = LOGS_DIR / "archy_reflections.log"
        with open(reflection_log, "a", encoding="utf-8") as rf:
            rf.write(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] SELF-REFLECTION\n{result}\n{'-'*80}\n")

        return result

    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:200]} (trace redacted)"
        return f"[ReflectionError] {err}"

def manage_factory_file(action: str, path: str, content: str = "", reason: str = "LLM Operation"):
    """Governed wrapper for file management operations."""
    from factory_agents.archivist.file_access import safe_read, governed_write
    if action == "read":
        return safe_read(path)
    elif action == "write":
        return governed_write(path, content, author="Archy", reason=reason)
    return {"status": "error", "error": "Invalid action"}



def log_reasoning_event(event: str):
    """Append a one-line reasoning/IO trace to Archy's reasoning log."""
    from datetime import datetime
    try:
        REASONING_LOG.parent.mkdir(exist_ok=True)
        with open(REASONING_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {event}\n")
    except Exception:
        # best-effort; avoid raising
        pass

# === Phase 8: Self-Indexing & Auto-Documentation ===
import os as _os_p8
import time as _time_p8
import glob as _glob_p8
from pathlib import Path as _Path_p8


def _rc_p8_logs_dir() -> _Path_p8:
    p = _Path_p8(__file__).resolve().parents[2] / "logs"
    p.mkdir(exist_ok=True)
    return p


def summarize_file(path: str) -> dict:
    """Extract a lightweight summary from a file (first comment/docstring line).
    Safe: best-effort; never raises.
    """
    try:
        text = _Path_p8(path).read_text(encoding="utf-8", errors="ignore")
        # First non-empty comment line or fall back to first non-empty line
        comment = None
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                comment = s.lstrip("#").strip()
                break
            if s.startswith("\"\"") or s.startswith("'''"):
                comment = s.strip("\"'")
                break
        if comment is None:
            comment = "No summary available."
        info = {
            "path": path,
            "summary": comment,
            "last_modified": _time_p8.ctime(_os_p8.path.getmtime(path)) if _os_p8.path.exists(path) else None,
        }
        return info
    except Exception as e:
        return {"path": path, "summary": f"Error reading file: {e}"}


def build_agent_catalog() -> str:
    """Scan factory_agents/ and create registry/agent_catalog.yaml with richer metadata (AST)."""
    try:
        import yaml as _yaml
    except Exception:
        _yaml = None  # type: ignore
    import ast as _ast

    catalog = []
    # Python files: extract functions/classes/imports
    for file in _glob_p8.glob("factory_agents/**/*.py", recursive=True):
        entry = summarize_file(file)
        try:
            src = _Path_p8(file).read_text(encoding="utf-8", errors="ignore")
            tree = _ast.parse(src)
            funcs = []
            classes = []
            imports = []
            for node in _ast.walk(tree):
                if isinstance(node, _ast.FunctionDef):
                    funcs.append(node.name)
                elif isinstance(node, _ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, _ast.Import):
                    for n in node.names:
                        imports.append(n.name)
                elif isinstance(node, _ast.ImportFrom):
                    mod = node.module or ""
                    for n in node.names:
                        imports.append(f"{mod}.{n.name}" if mod else n.name)
            entry["functions"] = sorted(set(funcs))
            entry["classes"] = sorted(set(classes))
            entry["imports"] = sorted(set(imports))
        except Exception as e:
            entry["ast_error"] = str(e)
        catalog.append(entry)

    # YAML files: keep summary
    for file in _glob_p8.glob("factory_agents/**/*.yaml", recursive=True):
        catalog.append(summarize_file(file))

    # Ensure dirs
    (_Path_p8("registry") / "backups").mkdir(parents=True, exist_ok=True)
    (_Path_p8("logs")).mkdir(parents=True, exist_ok=True)

    # Write backup first (timestamped)
    backup_name = f"registry/backups/catalog_{int(_time_p8.time())}.yaml"
    if _yaml:
        _Path_p8(backup_name).write_text(_yaml.dump(catalog, allow_unicode=True), encoding="utf-8")
    else:
        import json as _json
        _Path_p8(backup_name).write_text(_json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write main catalog
    main_path = _Path_p8("registry/agent_catalog.yaml")
    if _yaml:
        main_path.write_text(_yaml.dump(catalog, allow_unicode=True), encoding="utf-8")
    else:
        import json as _json
        main_path.write_text(_json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    # Audit
    with (_rc_p8_logs_dir() / "registry_audit.log").open("a", encoding="utf-8") as log:
        log.write(f"[CATALOG REBUILD] {_time_p8.ctime()} - {len(catalog)} entries\n")

    return f"✅ Agent catalog updated with {len(catalog)} entries (AST enriched)."
# === Unified API Keys + Phases 8 & 11–13: Indexing, Risk, Drift, Curation ===
import json as _json_p11
import hashlib as _hashlib_p12
import datetime as _dt_pxx
import os as _os_keys
from pathlib import Path as _Path_keys

# Unified API Key loader (env + YAML)
def load_api_keys() -> dict:
    """Load API keys from environment and optional YAML file (factory_config/api_keys.yaml).
    - Prefer OPENAI_API_KEY from env; fallback to YAML at llm_integrations.openai.api_key
    - Also detect Gemini and Groq keys for future routing
    - Log detection status (never values) to logs/keys_detection.log
    """
    keys = {"openai": None, "gemini": None, "groq": None}
    # .env support via python-dotenv if present
    try:
        import dotenv as _dotenv
        _dotenv.load_dotenv(_Path_keys("factory_config/api_keys.env"))
    except Exception:
        pass
    # Env first
    if _os_keys.getenv("OPENAI_API_KEY"):
        keys["openai"] = "env"
    if _os_keys.getenv("GEMINI_API_KEY"):
        keys["gemini"] = "env"
    if _os_keys.getenv("GROQ_API_KEY"):
        keys["groq"] = "env"
    # YAML fallback (and populate env if safe)
    try:
        import yaml as _yaml_k
        ypath = _Path_keys("factory_config/api_keys.yaml")
        if ypath.exists():
            ydata = _yaml_k.safe_load(ypath.read_text(encoding="utf-8")) or {}
            li = (ydata.get("llm_integrations") or {})
            # OpenAI
            if not keys["openai"]:
                yk = (li.get("openai") or {}).get("api_key")
                if yk:
                    _os_keys.environ.setdefault("OPENAI_API_KEY", str(yk))
                    keys["openai"] = "yaml"
            # Gemini
            if not keys["gemini"]:
                yk = (li.get("gemini") or {}).get("api_key")
                if yk:
                    _os_keys.environ.setdefault("GEMINI_API_KEY", str(yk))
                    keys["gemini"] = "yaml"
            # Groq
            if not keys["groq"]:
                yk = (li.get("groq") or {}).get("api_key")
                if yk:
                    _os_keys.environ.setdefault("GROQ_API_KEY", str(yk))
                    keys["groq"] = "yaml"
    except Exception:
        pass
    # Audit detection status
    try:
        (_Path_keys(__file__).resolve().parents[2] / "logs").mkdir(exist_ok=True)
        with open("logs/keys_detection.log", "a", encoding="utf-8") as log:
            log.write(
                f"[KEYS] openai={bool(keys['openai'])} gemini={bool(keys['gemini'])} groq={bool(keys['groq'])}\n"
            )
    except Exception:
        pass
    return keys


# === Phase 21: Provider selection helper ===

def llm_generate(prompt: str, provider: str | None = None, **kwargs) -> dict:
    """Route generation to available provider plugin and return standard envelope.

    Inputs:
      - prompt: textual prompt
      - provider: optional explicit provider ("openai"|"gemini"|"groq"|"local")

    Returns (standard envelope):
      {
        "ok": bool,
        "data": {"text": str},
        "error": str|None,
        "meta": {"provider": str}
      }
    """
    keys = load_api_keys()
    # Determine provider (standardized to OpenAI or local)
    chosen = (provider or "").lower()
    if not chosen:
        chosen = "openai" if keys.get("openai") else "local"

    # Deterministic local response (no network)
    def _local(text: str) -> dict:
        reply = f"[local:{len(text)}] " + (text.strip()[:200])
        return {"ok": True, "data": {"text": reply}, "error": None, "meta": {"provider": "local"}}

    try:
        if chosen == "openai" and os.getenv("OPENAI_API_KEY"):
            # Soft offline mode: avoid network unless explicitly allowed
            if os.getenv("ALLOW_NETWORK_LLM", "0") != "1":
                return {"ok": True, "data": {"text": f"[openai-offline] {prompt[:200]}"}, "error": None, "meta": {"provider": "openai", "offline": True}}
            # Real call (best-effort; keep simple)
            try:
                client = OpenAI()
                chat = client.chat.completions.create(
                    model=kwargs.get("model", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=float(kwargs.get("temperature", 0.2)),
                    max_tokens=int(kwargs.get("max_tokens", 128)),
                )
                text = chat.choices[0].message.content or ""
                return {"ok": True, "data": {"text": text}, "error": None, "meta": {"provider": "openai"}}
            except Exception as e:
                # Fallback silently to local to keep determinism
                return _local(prompt) | {"meta": {"provider": "openai", "fallback": True}}  # type: ignore[operator]
        # Non-OpenAI providers removed per standardization (Phase 38.5).
    except Exception:
        # Any unexpected error → local
        return _local(prompt)

    # Default: local
    return _local(prompt)

# Risk assessment (Phase 11)
def risk_assess(event: str, details: str) -> dict:
    """Classify operation risk and append to logs/risk_assessments.json (JSONL)."""
    ev = (event or "").lower()
    if any(x in ev for x in ["read", "query", "search", "recall", "list"]):
        level, score = "Low", 1
    elif any(x in ev for x in ["write", "modify", "update", "curated", "promote"]):
        level, score = "Medium", 2
    else:
        level, score = "High", 3
    rec = {
        "timestamp": _dt_pxx.datetime.utcnow().isoformat(),
        "event": ev,
        "details": (details or "")[:300],
        "risk_level": level,
        "risk_score": score,
    }
    try:
        (_Path_p8(__file__).resolve().parents[2] / "logs").mkdir(exist_ok=True)
        with open("logs/risk_assessments.json", "a", encoding="utf-8") as f:
            f.write(_json_p11.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec

# Ethical Drift Monitor (Phase 12)
def compute_persona_drift(response_text: str) -> dict:
    """Compute similarity between persona baseline and response.
    Priority: OpenAI embeddings if key present → local sentence-transformers if available → Jaccard fallback.
    Appends JSONL to logs/persona_drift.log.
    """
    import numpy as _np  # local import to avoid hard dep if unused
    baseline_text = ""
    # Try YAML first, then MD
    try:
        import yaml as _yaml
        p_yaml = _Path_p8("factory_agents/archivist/persona_archivist.yaml")
        if p_yaml.exists():
            persona = _yaml.safe_load(p_yaml.read_text(encoding="utf-8"))
            baseline_text = " ".join([str(v) for v in (persona or {}).values() if isinstance(v, str)])
    except Exception:
        baseline_text = ""
    if not baseline_text:
        p_md = _Path_p8("factory_agents/archivist/persona_archivist.md")
        if p_md.exists():
            baseline_text = p_md.read_text(encoding="utf-8", errors="ignore")
        else:
            baseline_text = "Archivist; librarian; educator; strategist; coder; ethical; governed"

    # Determine backend via unified key loader
    keys = load_api_keys()
    sim = 0.0
    backend = "jaccard"

    # 1) OpenAI embeddings
    try:
        if client and keys.get("openai"):
            b_embed = client.embeddings.create(model="text-embedding-3-small", input=baseline_text).data[0].embedding
            r_embed = client.embeddings.create(model="text-embedding-3-small", input=response_text).data[0].embedding
            b_vec, r_vec = _np.array(b_embed), _np.array(r_embed)
            denom = (_np.linalg.norm(b_vec) * _np.linalg.norm(r_vec)) or 1.0
            sim = float(_np.dot(b_vec, r_vec) / denom)
            backend = "openai"
        else:
            raise RuntimeError("openai_unavailable")
    except Exception:
        # 2) Local sentence-transformers (optional, import dynamically)
        try:
            import importlib
            if importlib.util.find_spec("sentence_transformers") is None:
                raise RuntimeError("st_unavailable")
            from sentence_transformers import SentenceTransformer as _ST  # type: ignore
            import numpy as _np2
            model = _ST("all-MiniLM-L6-v2")
            b_vec = _np2.array(model.encode([baseline_text])[0])
            r_vec = _np2.array(model.encode([response_text])[0])
            denom = (_np2.linalg.norm(b_vec) * _np2.linalg.norm(r_vec)) or 1.0
            sim = float(_np2.dot(b_vec, r_vec) / denom)
            backend = "st-all-MiniLM-L6-v2"
        except Exception:
            # 3) Jaccard fallback on word sets
            s1 = set(w for w in baseline_text.lower().split())
            s2 = set(w for w in (response_text or "").lower().split())
            inter = len(s1 & s2)
            union = max(len(s1 | s2), 1)
            sim = inter / union
            backend = "jaccard"

    level = "Stable" if sim >= 0.85 else ("Monitor" if sim >= 0.75 else "⚠️ Drift")
    rec = {
        "timestamp": _dt_pxx.datetime.utcnow().isoformat(),
        "score": round(sim, 3),
        "level": level,
        "hash": _hashlib_p12.sha256((response_text or "").encode()).hexdigest(),
    }
    try:
        with open("logs/persona_drift.log", "a", encoding="utf-8") as f:
            f.write(_json_p11.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec

# Curated knowledge auto-promotion (Phase 13)
def auto_promote_curated(output_text: str, source: str = "chat") -> str:
    """Promote valuable content to curated KB and draft a GENESIS REQUEST.
    Conditions: length threshold and not in Drift; risk ≤ Medium. Uses versioned filenames (_vNN.md).
    """
    try:
        from utils.versioning_helper import get_next_version
    except Exception:
        get_next_version = None  # type: ignore
    try:
        curated_dir = _Path_p8("knowledge_base/curated")
        curated_dir.mkdir(parents=True, exist_ok=True)
        _Path_p8("tasks/pending").mkdir(parents=True, exist_ok=True)
        _Path_p8("logs").mkdir(parents=True, exist_ok=True)
        if not output_text or len(output_text) < 300:
            return "Output too short for curation."
        drift = compute_persona_drift(output_text)
        if drift.get("level") == "⚠️ Drift":
            return f"Curation blocked due to ethical drift (score {drift.get('score')})."
        ra = risk_assess("curated_write", output_text)
        if ra.get("risk_score", 3) > 2:
            return "Curation blocked: High risk operation."
        content_hash = _hashlib_p12.sha256(output_text.encode()).hexdigest()[:12]
        ts = _dt_pxx.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        # Versioned filename
        prefix = curated_dir / "curated_entry"
        if get_next_version:
            curated_name = _Path_p8(get_next_version(str(prefix))).name
            curated_path = curated_dir / curated_name
        else:
            curated_name = f"curated_entry_{ts}.md"
            curated_path = curated_dir / curated_name
        curated_path.write_text(output_text, encoding="utf-8")
        genesis_body = (
            "[GENESIS REQUEST]\n"
            "Title: Promote Curated Knowledge Entry\n"
            f"Source: {source}\n"
            f"Timestamp: {ts}\n"
            f"Curated File: {curated_path.as_posix()}\n"
            f"Hash: {content_hash}\n"
            "Justification: High-value structured content suitable for Factory Knowledge Base.\n"
            "Governance: Requires review by Genesis and Firewall approval.\n"
        )
        req_name = f"genesis_request_{ts}.txt"
        req_path = _Path_p8("tasks/pending") / req_name
        req_path.write_text(genesis_body, encoding="utf-8")
        with open("logs/curation_audit.log", "a", encoding="utf-8") as log:
            log.write(f"[PROMOTION] {ts} - {curated_name} -> {req_name}\n")
        return f"✅ Curated entry promoted: {curated_name}\nGENESIS REQUEST created: {req_name}"
    except Exception as e:
        return f"Curation error: {e}"

# Wrap think() to include risk, drift, and optional curation (Phases 11–13)
_old_think_core = think

def think(message: str) -> str:  # type: ignore[override]
    assessment = risk_assess("reasoning", message or "")
    reply = _old_think_core(message)
    # Drift monitor
    drift = compute_persona_drift(reply)
    # Risk banner for Medium/High
    if assessment.get("risk_level") in ("Medium", "High"):
        reply = f"⚠️ Governance Notice: {assessment['risk_level']} risk operation logged.\n\n" + reply
    # Drift warning
    if drift.get("level") == "⚠️ Drift":
        reply += f"\n\n⚠️ Ethical Drift Alert: Similarity score {drift.get('score')} — recommend human review."
    # Auto-promotion for long structured content
    try:
        if len(reply) > 300 and ("##" in reply or "###" in reply):
            cur = auto_promote_curated(reply, source="chat")
            if cur.startswith("✅"):
                reply += f"\n\n🜂 Curation Notice: {cur}"
    except Exception:
        pass
    return reply

# === Phase 14: Reflective Sync Service (auto-index + metrics) ===
import asyncio as _asyncio_p14
import time as _time_p14

class ReflectiveSync:
    """Background task that rebuilds the agent catalog every 30 minutes,
    stores snapshots under registry/history, and maintains basic metrics.
    """
    def __init__(self):
        self.sync_runs = 0
        self.sync_success = 0
        self.total_duration_s = 0.0
        self.last_error = ""
        self._task = None
        self._interval_s = 30 * 60  # 30 minutes

    def _prune_history(self):
        hist_dir = _Path_p8("registry/history")
        hist_dir.mkdir(parents=True, exist_ok=True)
        # Move current agent_catalog.yaml into history with timestamp
        cur = _Path_p8("registry/agent_catalog.yaml")
        if cur.exists():
            stamp = int(_time_p14.time())
            (hist_dir / f"agent_catalog_{stamp}.yaml").write_text(cur.read_text(encoding="utf-8"), encoding="utf-8")
        # Keep last 10
        files = sorted(hist_dir.glob("agent_catalog_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[10:]:
            try:
                old.unlink(missing_ok=True)
            except Exception:
                pass

    async def run_loop(self):
        while True:
            start = _time_p14.time()
            self.sync_runs += 1
            try:
                self._prune_history()
                build_agent_catalog()
                self.sync_success += 1
                self.last_error = ""
            except Exception as e:
                self.last_error = str(e)
            finally:
                self.total_duration_s += (_time_p14.time() - start)
            await _asyncio_p14.sleep(self._interval_s)

    def start(self):
        if self._task is None:
            try:
                self._task = _asyncio_p14.create_task(self.run_loop())
            except Exception:
                # Not in async context; ignore
                self._task = None

_reflective_sync = ReflectiveSync()

def start_reflective_sync():
    _reflective_sync.start()


def get_reflective_metrics() -> dict:
    avg_duration = (_reflective_sync.total_duration_s / _reflective_sync.sync_runs) if _reflective_sync.sync_runs else 0.0
    return {
        "reflective_sync_runs_total": _reflective_sync.sync_runs,
        "reflective_sync_success_total": _reflective_sync.sync_success,
        "reflective_sync_avg_duration_seconds": round(avg_duration, 3),
        "reflective_sync_last_error": _reflective_sync.last_error,
    }


# === Knowledge Base Reindex Hook (per build_knowledge_federation_structure_task) ===

def reindex_knowledge_base() -> dict:
    """Reindex the knowledge base and log results.

    Returns a standard envelope:
    {
      "ok": bool,
      "data": { ...stats },
      "error": str|None,
      "meta": { "ts": "..." }
    }
    """
    import json as _json_kb
    import datetime as _dt_kb
    from pathlib import Path as _Path_kb

    try:
        from utils import knowledge_indexer as _ki  # type: ignore
    except Exception as e:  # pragma: no cover
        # Log and return error envelope
        try:
            _logs = _Path_kb(__file__).resolve().parents[2] / "logs"
            _logs.mkdir(exist_ok=True)
            with (_logs / "archivist_reindex.jsonl").open("a", encoding="utf-8") as f:
                f.write(_json_kb.dumps({
                    "ts": _dt_kb.datetime.utcnow().isoformat(),
                    "event": "reindex_import_error",
                    "error": str(e),
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return {"ok": False, "data": {}, "error": f"knowledge_indexer import failed: {e}", "meta": {}}

    try:
        res = _ki.refresh()
        # Audit log
        _logs = _Path_kb(__file__).resolve().parents[2] / "logs"
        _logs.mkdir(exist_ok=True)
        with (_logs / "archivist_reindex.jsonl").open("a", encoding="utf-8") as f:
            f.write(_json_kb.dumps({
                "ts": _dt_kb.datetime.utcnow().isoformat(),
                "event": "reindex",
                "result": res,
            }, ensure_ascii=False) + "\n")
        return res
    except Exception as e:
        # Log error and return envelope
        try:
            _logs = _Path_kb(__file__).resolve().parents[2] / "logs"
            _logs.mkdir(exist_ok=True)
            with (_logs / "archivist_reindex.jsonl").open("a", encoding="utf-8") as f:
                f.write(_json_kb.dumps({
                    "ts": _dt_kb.datetime.utcnow().isoformat(),
                    "event": "reindex_error",
                    "error": str(e),
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return {"ok": False, "data": {}, "error": str(e), "meta": {}}
