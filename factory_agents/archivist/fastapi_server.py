# Ensure repo root + src on sys.path for imports when run directly
try:
    import tools.startup  # type: ignore
except Exception:
    pass

from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Query
from pydantic import BaseModel
from factory_agents.archivist.reasoning_core import think, log_reasoning_event
from factory_agents.archivist.file_access import safe_read, governed_write, list_dir, safe_write
from factory_agents.archivist.web_client import router as web_router  # ✅ ensure this import exists
from factory_agents.archivist.curator_api import router as curator_router
import uvicorn
import re
import os
from datetime import datetime
from pathlib import Path
import json as _json
import httpx

# Optional MemoryEngine import (Phase 5)
try:
    from agent_factory.services.memory.engine import MemoryEngine  # type: ignore
except Exception:  # engine optional
    MemoryEngine = None  # type: ignore

# ===== Phase 2: Markdown Formatting helper and simple persistence =====
# Resolve project root deterministically
FACTORY_ROOT = Path(__file__).resolve()
while FACTORY_ROOT.name != "agent-factory" and FACTORY_ROOT.parent != FACTORY_ROOT:
    FACTORY_ROOT = FACTORY_ROOT.parent

LOGS_DIR = FACTORY_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
UI_FORMAT_LOG = LOGS_DIR / "ui_format_test.log"
PROC_LOG = LOGS_DIR / "archivist_memory.jsonl"
LONG_TERM_DIR = FACTORY_ROOT / "memory_store" / "long_term"
LONG_TERM_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR = FACTORY_ROOT / "artifacts" / "telemetry"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MEM_JSONL = ARTIFACTS_DIR / "archivist_memory_index.jsonl"

# Optional MemoryEngine instance (Phase 5)
_mem_engine = None
if MemoryEngine is not None:
    try:
        _mem_engine = MemoryEngine()
    except Exception:
        _mem_engine = None


def _append_line(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def _append_jsonl(path: Path, obj: dict) -> None:
    _append_line(path, _json.dumps(obj, ensure_ascii=False))


def _session_file() -> Path:
    ts = datetime.utcnow().strftime("%Y-%m-%d")
    return LONG_TERM_DIR / f"session_{ts}.jsonl"


def record_conversation(role: str, content: str) -> None:
    _append_jsonl(_session_file(), {"ts": datetime.utcnow().isoformat(), "role": role, "content": content})


def format_response(data):
    """Pretty-format all Archy responses for readability in Markdown style."""
    try:
        if isinstance(data, dict):
            status = data.get("status")
            # Directory listing
            if status == "success" and isinstance(data.get("items"), list):
                items_md = "\n".join([f"- {'📁' if i.get('type')=='dir' else '📄'} {i.get('name')}" for i in data["items"]])
                md = f"🜂 **Archy Report**\n## Directory Listing\n{items_md}"
                _append_line(UI_FORMAT_LOG, md)
                return md
            # File read
            if status == "success" and "content" in data:
                path = data.get("path", "")
                content = str(data.get("content", ""))
                snippet = content[:20000]  # generous cap for browser
                md = f"🜂 **Archy Report**\n## File Read\n**Path:** `{path}`\n\n```\n{snippet}\n```"
                _append_line(UI_FORMAT_LOG, md)
                return md
            # Requires confirmation
            if status == "requires_confirmation":
                md = f"🜂 **Archy Notice**\n⚠️ {data.get('message','Confirmation required.')}\n\nUse: `confirm overwrite <path>`"
                _append_line(UI_FORMAT_LOG, md)
                return md
            # Generic error
            if status == "error":
                md = f"🜂 **Archy Error**\n❗ {data.get('error','Unknown error')}\n**Path:** {data.get('path','')}"
                _append_line(UI_FORMAT_LOG, md)
                return md
            # Plain reply wrapper
            if "reply" in data and status == "success":
                md = f"🜂 **Archy Response**\n{data['reply']}"
                _append_line(UI_FORMAT_LOG, md)
                return md
            # Fallback pretty JSON
            md = f"🜂 **Archy Output**\n{_json.dumps(data, indent=2, ensure_ascii=False)}"
            _append_line(UI_FORMAT_LOG, md)
            return md
        if isinstance(data, str):
            lines = data.replace("\r\n", "\n").strip()
            md = f"🜂 **Archy Response**\n{lines}"
            _append_line(UI_FORMAT_LOG, md)
            return md
        md = f"🜂 **Archy Output**\n{data}"
        _append_line(UI_FORMAT_LOG, md)
        return md
    except Exception as _e:  # never break the chat on formatting
        return str(data)


app = FastAPI(title="Archivist Agent API")

# Mount extra governance/federation/metrics endpoints
try:
    from factory_agents.archivist import extra_endpoints as _xtra
    app.include_router(_xtra.router)
except Exception:
    pass

# Startup: begin ReflectiveSync background task when possible
try:
    from factory_agents.archivist.reasoning_core import start_reflective_sync, get_reflective_metrics
    @app.on_event("startup")
    async def _startup_reflective_sync():
        try:
            start_reflective_sync()
        except Exception:
            pass
except Exception:
    def get_reflective_metrics():  # type: ignore
        return {}

# === Phase 21: Compliance verification scheduler ===
import asyncio as _asyncio_c

COMPLIANCE_METRICS = LOGS_DIR / "compliance_metrics.json"


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(_json.dumps(obj, ensure_ascii=False, indent=2))


async def _compute_and_store_compliance_metrics() -> dict:
    ts = datetime.utcnow().isoformat()
    try:
        ledger = FACTORY_ROOT / "governance" / "compliance_ledger.jsonl"
        ledger_entries = 0
        if ledger.exists():
            with ledger.open("r", encoding="utf-8") as f:
                for _ in f:
                    ledger_entries += 1
        firewall_log = FACTORY_ROOT / "governance" / "firewall_audit.log"
        firewall_events = 0
        if firewall_log.exists():
            firewall_events = sum(1 for _ in firewall_log.open("r", encoding="utf-8"))
        # last drift score
        drift_log = FACTORY_ROOT / "logs" / "persona_drift.log"
        last_drift = None
        if drift_log.exists():
            try:
                last_lines = drift_log.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:]
                for ln in reversed(last_lines):
                    obj = _json.loads(ln)
                    last_drift = float(obj.get("score"))
                    break
            except Exception:
                last_drift = None
        metrics = {
            "ts": ts,
            "ledger_entries": ledger_entries,
            "firewall_events": firewall_events,
            "last_drift_score": last_drift,
            "ok": True,
        }
    except Exception as e:
        metrics = {"ts": ts, "ok": False, "error": str(e)}
    _write_json(COMPLIANCE_METRICS, metrics)
    return metrics


async def _compliance_scheduler_loop():
    # Run once at startup, then every 24h
    await _compute_and_store_compliance_metrics()
    while True:
        try:
            await _asyncio_c.sleep(24 * 60 * 60)
            await _compute_and_store_compliance_metrics()
        except Exception:
            await _asyncio_c.sleep(60)


@app.on_event("startup")
async def _startup_compliance_scheduler():
    try:
        _asyncio_c.create_task(_compliance_scheduler_loop())
    except Exception:
        pass

# === Governance Review Endpoint ===
class GovernanceEvent(BaseModel):
    event: str
    level: str | None = None
    details: str | None = None

@app.post("/governance/review")
async def governance_review(evt: GovernanceEvent):
    try:
        gov_dir = FACTORY_ROOT / "governance"
        gov_dir.mkdir(parents=True, exist_ok=True)
        log_path = gov_dir / "firewall_audit.log"
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "event": evt.event,
            "level": (evt.level or ""),
            "details": (evt.details or ""),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
        # Optional risk hook
        try:
            from factory_agents.archivist import reasoning_core as _rc_g
            _rc_g.risk_assess(evt.event, evt.details or "")
        except Exception:
            pass
        return {"ok": True, "logged": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Mount the web chat router
app.include_router(web_router)
# ✅ Mount curator API under /curator
app.include_router(curator_router, prefix="/curator")

# ===== Phase 4: Web Search (Serper or stub) =====
SERPER_KEY = os.getenv("SERPER_API_KEY") or os.getenv("INTEGRATION_SERPER_KEY")
SERPER_ENDPOINT = "https://google.serper.dev/search"

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search_api(req: SearchRequest):
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query required")
    ts = datetime.utcnow().isoformat()
    if not SERPER_KEY:
        # graceful fallback
        results = [{"title": "Search unavailable", "url": "", "snippet": "Provide SERPER_API_KEY to enable external search.", "ts": ts, "external": True}]
        return {"status": "success", "results": results}
    try:
        headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
        payload = {"q": q}
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(SERPER_ENDPOINT, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        items = data.get("organic", []) or []
        results = [{
            "title": it.get("title", ""),
            "url": it.get("link", ""),
            "snippet": it.get("snippet", ""),
            "ts": ts,
            "external": True
        } for it in items[:5]]
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/health")
def health():
    try:
        metrics = get_reflective_metrics()
    except Exception:
        metrics = {}
    return {"ok": True, "service": "archivist", "reflective_sync": metrics}

@app.get("/hello")
def hello():
    return {"message": "Hello from Archy — the Archivist agent is alive and ready."}

class ReadRequest(BaseModel):
    path: str

class ListRequest(BaseModel):
    path: str | None = None

# ===== Phase 5: Vector memory endpoints (with graceful fallback) =====
class MemoryDoc(BaseModel):
    text: str
    metadata: dict | None = None

class MemoryQuery(BaseModel):
    query: str
    top_k: int = 5

@app.post("/memory/remember")
async def memory_remember(doc: MemoryDoc):
    ts = datetime.utcnow().isoformat()
    if _mem_engine is not None:
        try:
            _mem_engine.add_documents([doc.text], metadata=doc.metadata or {"ts": ts, "source": "archivist"})
            _append_jsonl(MEM_JSONL, {"ts": ts, "text": doc.text, "meta": doc.metadata, "backend": "engine"})
            return {"status": "success", "backend": "engine"}
        except Exception as e:
            # fall through to stub
            _append_line(LOGS_DIR / "file_access_audit.log", f"[MEMORY-ENGINE-ERROR] {e}")
    # fallback stub: JSONL store + naive index
    _append_jsonl(MEM_JSONL, {"ts": ts, "text": doc.text, "meta": doc.metadata, "backend": "stub"})
    return {"status": "success", "backend": "stub"}

@app.post("/memory/search")
async def memory_search(q: MemoryQuery):
    if _mem_engine is not None:
        try:
            res = _mem_engine.search(q.query, top_k=q.top_k)
            return {"status": "success", "results": res}
        except Exception as e:
            _append_line(LOGS_DIR / "file_access_audit.log", f"[MEMORY-ENGINE-ERROR] {e}")
    # fallback: scan JSONL and score by substring count
    results: list[dict] = []
    if MEM_JSONL.exists():
        for line in MEM_JSONL.read_text(encoding="utf-8").splitlines():
            try:
                rec = _json.loads(line)
                text = rec.get("text", "")
                score = text.lower().count(q.query.lower())
                if score > 0:
                    results.append({"text": text[:300], "score": score, "meta": rec.get("meta"), "ts": rec.get("ts")})
            except Exception:
                continue
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"status": "success", "results": results[: q.top_k]}

# ===== Phase 6: Procedural log + simulation =====
class SimulateRequest(BaseModel):
    goal: str
    steps: int = 3

@app.post("/simulate")
async def simulate(req: SimulateRequest):
    steps = max(1, min(10, req.steps))
    transcript = []
    for i in range(steps):
        msg = {"ts": datetime.utcnow().isoformat(), "role": "agent", "content": f"Step {i+1}/{steps}: working on {req.goal}"}
        transcript.append(msg)
        _append_jsonl(PROC_LOG, {"event": "simulate", **msg})
    return {"status": "success", "transcript": transcript}

# ===== Phase 7: Conversation history =====
@app.get("/conversation/history")
async def history(limit: int = Query(20, ge=1, le=500)):
    sf = _session_file()
    out: list[dict] = []
    if sf.exists():
        lines = sf.read_text(encoding="utf-8").splitlines()[-limit:]
        for ln in lines:
            try:
                out.append(_json.loads(ln))
            except Exception:
                continue
    return {"status": "success", "items": out}

@app.post("/read_file")
async def read_file(req: ReadRequest):
    return safe_read(req.path)

@app.post("/list_dir")
async def list_dir_api(req: ListRequest):
    return list_dir(req.path)

# ===== Phase 3: Upload endpoint =====
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        upload_dir = FACTORY_ROOT / "knowledge_base" / "uploaded"
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / file.filename
        with target.open("wb") as fout:
            fout.write(await file.read())
        _append_line(LOGS_DIR / "file_access_audit.log", f"[UPLOAD] {file.filename} -> {target}")
        md = format_response({"status": "success", "reply": f"📂 File uploaded: {file.filename}"})
        return {"status": "success", "message": f"File uploaded: {file.filename}", "path": str(target), "reply": md}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    prompt = data.get("message", "").strip()
    record_conversation("user", prompt)

    # ✅ Overwrite confirmation command
    if prompt.lower().startswith("confirm overwrite "):
        path = prompt[len("confirm overwrite "):].strip()
        result = safe_write(path, "", confirm=True)
        if isinstance(result, dict) and result.get("status") == "success":
            log_reasoning_event(f"Overwrite confirmed for: {result.get('path')}")
            md = format_response({"status": "success", "reply": f"✅ Overwrite confirmed: {result.get('path')}"})
            record_conversation("assistant", md)
            return {"reply": md}
        log_reasoning_event(f"Overwrite confirm failed for: {path} → {result}")
        md = format_response({"status": "error", "error": "Confirm overwrite failed", "path": path})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🗂️ Phase 8: Update registry catalog
    if prompt.lower().strip() == 'update registry':
        from factory_agents.archivist import reasoning_core as _rc
        result = _rc.build_agent_catalog()
        md = format_response({"status": "success", "reply": result})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🩺 Phase 9: Health check
    if prompt.lower().strip() == 'health check':
        try:
            from factory_agents.archivist import healthcheck as _hc
            report = _hc.run_health_diagnostics()
        except Exception as e:
            report = f"Healthcheck error: {e}"
        md = format_response({"status": "success", "reply": report})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🔐 Phase 11: Risk summary
    if prompt.lower().strip() == 'risk summary':
        import json as _json
        path = os.path.join('logs', 'risk_assessments.json')
        if not os.path.exists(path):
            md = format_response({"status": "success", "reply": "No risk assessments logged yet."})
            record_conversation("assistant", md)
            return {"reply": md}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-10:]
            entries = [_json.loads(l) for l in lines]
            summary = '\n'.join([f"- {e.get('timestamp')}: {e.get('event')} ({e.get('risk_level')})" for e in entries])
        except Exception as e:
            summary = f"Error reading risk log: {e}"
        md = format_response({"status": "success", "reply": f"🜂 **Recent Risk Assessments**\n{summary}"})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🧭 Phase 12: Drift status
    if prompt.lower().strip() == 'drift status':
        import json as _json
        path = os.path.join('logs', 'persona_drift.log')
        if not os.path.exists(path):
            md = format_response({"status": "success", "reply": "No drift logs yet."})
            record_conversation("assistant", md)
            return {"reply": md}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-5:]
            entries = [_json.loads(l) for l in lines]
            summary = '\n'.join([f"- {e.get('timestamp')} | Score: {e.get('score')} | Level: {e.get('level')}" for e in entries])
        except Exception as e:
            summary = f"Error reading drift log: {e}"
        md = format_response({"status": "success", "reply": f"🜂 **Recent Ethical Drift Reports**\n{summary}"})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🗃️ Phase 13: Manual promote knowledge
    if prompt.lower().strip() == 'promote knowledge':
        from factory_agents.archivist import reasoning_core as _rc
        result = _rc.auto_promote_curated('Manual promotion initiated by user.', 'manual')
        md = format_response({"status": "success", "reply": result})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🤖 Phase 10: Autonomous crew simulation
    if prompt.lower().startswith('simulate autonomous crew '):
        topic = prompt.replace('simulate autonomous crew ', '').strip()
        try:
            from factory_agents.archivist.simulation_core import AutonomousCrew
            sim = AutonomousCrew()
            reply = sim.simulate_autonomous_crew(topic, rounds=3)
            md = format_response({"status": "success", "reply": reply})
        except Exception as e:
            md = format_response({"status": "error", "error": f"Simulation error: {e}"})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🔍 Detect read requests
    read_match = re.search(r"\bread\s+([\w\-/\\\.]+)", prompt, re.IGNORECASE)
    if read_match:
        path = read_match.group(1)
        result = safe_read(path)
        log_reasoning_event(f"Read result for {path}: {result.get('status') if isinstance(result, dict) else 'n/a'}")
        md = format_response(result)
        record_conversation("assistant", md)
        return {"reply": md}

    # ✍️ Detect write requests
    write_match = re.search(r"\bwrite\s+([\w\-/\\\.]+)\s*[:=]\s*(.*)", prompt, re.IGNORECASE)
    if write_match:
        path, content = write_match.groups()
        result = governed_write(path, content)
        log_reasoning_event(f"Write result for {path}: {result}")
        md = format_response(result)
        record_conversation("assistant", md)
        return {"reply": md}

    # 📁 Detect list requests: "list <path>" or NL queries
    list_match = re.search(r"\blist\s+([\w\-/\\\.]+)", prompt, re.IGNORECASE)
    if list_match:
        lpath = list_match.group(1)
        result = list_dir(lpath)
        log_reasoning_event(f"List result for {lpath}: {result.get('status') if isinstance(result, dict) else 'n/a'}")
        md = format_response(result)
        record_conversation("assistant", md)
        return {"reply": md}

    lower = prompt.lower()
    keywords = [
        "show files", "see files", "see my files", "browse files", "what files",
        "list files", "agent factory files", "access files", "access folders", "files or folders", "access the repo", "access the root"
    ]
    if any(kw in lower for kw in keywords):
        root_res = list_dir(None)
        tip = "I can access governed project files under the project root.\nTry: 'list .' for root, 'list knowledge_base', or 'read factory_governance/genesis_principles.yaml'"
        if isinstance(root_res, dict) and root_res.get("status") == "success":
            items = root_res.get("items", [])
            sample = ", ".join([it.get("name") for it in items[:10]])
            tip += f"\nTop-level entries: {sample}"
        md = format_response({"status": "success", "reply": tip})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🔎 Detect web search intent
    search_match = re.search(r"\bsearch\s+(.+)$", prompt, re.IGNORECASE)
    if search_match:
        q = search_match.group(1).strip()
        res = await search_api(SearchRequest(query=q))
        if res.get("status") == "success":
            lines = []
            for it in res.get("results", []):
                title = it.get("title", "(no title)")
                url = it.get("url", "")
                snippet = it.get("snippet", "")
                lines.append(f"- [external] **{title}** — {snippet}\n  {url}")
            md = format_response({"status": "success", "reply": "\n".join(lines) or "No results."})
            record_conversation("assistant", md)
            return {"reply": md}
        md = format_response({"status": "error", "error": res.get("error", "search failed")})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🧠 Memory intents: remember / recall
    remember_match = re.search(r"\bremember\s+([^:：]+)[:：]\s*(.+)$", prompt, re.IGNORECASE)
    if remember_match:
        summary, content = remember_match.groups()
        await memory_remember(MemoryDoc(text=f"{summary.strip()}: {content.strip()}", metadata={"summary": summary.strip()}))
        md = format_response({"status": "success", "reply": f"🧠 Remembered: {summary.strip()}"})
        record_conversation("assistant", md)
        return {"reply": md}

    recall_match = re.search(r"\brecall\s+(.+)$", prompt, re.IGNORECASE)
    if recall_match:
        q = recall_match.group(1).strip()
        res = await memory_search(MemoryQuery(query=q, top_k=5))
        if res.get("status") == "success":
            items = res.get("results", [])
            lines = [f"- score {it.get('score', it.get('metadata',{}))}: {it.get('text','')[:200]}" for it in items]
            md = format_response({"status": "success", "reply": "\n".join(lines) or "No matches."})
            record_conversation("assistant", md)
            return {"reply": md}
        md = format_response({"status": "error", "error": res.get("error", "recall failed")})
        record_conversation("assistant", md)
        return {"reply": md}

    # 🧠 Default reasoning if no file operation matched
    reply_text = think(prompt)
    md = format_response(reply_text)
    record_conversation("assistant", md)
    return {"reply": md}


if __name__ == "__main__":
    uvicorn.run("factory_agents.archivist.fastapi_server:app", host="0.0.0.0", port=5065)
