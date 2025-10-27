import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv, find_dotenv
from crewai import Agent, Task, Crew, Process, LLM

# Ensure repo root and src/ are on path
import tools.startup  # noqa: F401
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from agent_factory.services.audit.audit_logger import (
    log_agent_run,
    log_event,
)
from agent_factory.utils.procedural_memory_pg import trace_run


# -------------------------------
# GenesisOrchestrator (admin API)
# -------------------------------
class GenesisOrchestrator:
    """Lightweight orchestration facade for admin tooling.

    Persists state under data/genesis_state.json and logs under
    logs/genesis_session_YYYYMMDD.log. This class is intentionally minimal
    and does not start the Crew itself; it exposes admin-friendly hooks.
    """

    def __init__(self) -> None:
        self.repo_root = PROJECT_ROOT
        self.data_dir = self.repo_root / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "genesis_state.json"
        self.logs_dir = self.repo_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        # Runtime process tracking (best-effort)
        self._listener_pid_path = self.data_dir / "genesis_listener.pid"
        # Health monitor defaults (env-configurable)
        try:
            self.healthcheck_interval = int(os.getenv("GENESIS_HEALTHCHECK_INTERVAL", "60"))
        except Exception:
            self.healthcheck_interval = 60
        try:
            self.max_failures = int(os.getenv("GENESIS_MAX_FAILURES", "3"))
        except Exception:
            self.max_failures = 3
        self.healthcheck_failures = 0
        self.listener_port: Optional[int] = None
        self.listener_active: bool = False
        self._health_thread_started: bool = False

    # ---- internal helpers ----
    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                import json
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                return {"state": "error"}
        return {"state": "idle", "active": False}

    def _save_state(self, payload: Dict[str, Any]) -> None:
        try:
            import json
            self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _log_line(self, text: str) -> None:
        day = datetime.now(timezone.utc).date().isoformat()
        path = self.logs_dir / f"genesis_session_{day}.log"
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(f"[{self._now()}] {text}\n")
        except Exception:
            pass

    def _latest_log_path(self) -> Path:
        day = datetime.now(timezone.utc).date().isoformat()
        path = self.logs_dir / f"genesis_session_{day}.log"
        return path

    # ---- health monitor ----
    def _emit_health_event(self, status: str) -> None:
        try:
            from datetime import datetime as _dt
            ts = _dt.utcnow().isoformat()
            # Log to session log for operator visibility
            self._log_line(f"[HealthEvent] status={status} port={getattr(self, 'listener_port', '')}")
            row = f"{ts},{getattr(self, 'listener_port', '')},{status},{self._load_state().get('mode')}\n"
            audit_dir = self.repo_root / "compliance" / "audit_log"
            audit_dir.mkdir(parents=True, exist_ok=True)
            (audit_dir / "genesis_health.csv").open("a", encoding="utf-8").write(row)
        except Exception:
            pass

    def _start_health_monitor(self) -> None:
        if self._health_thread_started:
            return
        self._health_thread_started = True

        def monitor() -> None:
            import time as _time
            import httpx as _httpx
            while True:
                try:
                    # Stop condition: not active or listener off
                    st = self._load_state()
                    if not st.get("active") or not bool(getattr(self, "listener_active", False)) or not getattr(self, "listener_port", None):
                        break
                    _time.sleep(int(getattr(self, "healthcheck_interval", 60)))
                    port = int(getattr(self, "listener_port", 0) or 0)
                    if port <= 0:
                        continue
                    try:
                        r = _httpx.get(f"http://127.0.0.1:{port}/ping", timeout=3.0)
                        ok = (r.status_code == 200) and (r.json().get("ok") is True)
                    except Exception as e:  # request error
                        ok = False
                        err = e
                    if ok:
                        self.healthcheck_failures = 0
                        self._log_line(f"[Health] OK on port {port}")
                        self._emit_health_event("ok")
                    else:
                        self.healthcheck_failures += 1
                        self._log_line(f"[Health] Failed check {self.healthcheck_failures}/{self.max_failures}")
                        self._emit_health_event("fail")
                        if self.healthcheck_failures >= int(getattr(self, "max_failures", 3)):
                            self._log_line("[Genesis] Listener unresponsive — attempting restart")
                            try:
                                # attempt restart
                                self.listen(port)
                                self.healthcheck_failures = 0
                                self._emit_health_event("restart")
                            except Exception as re:  # pragma: no cover
                                self._log_line(f"[Genesis] Listener restart failed: {re}")
                                self._emit_health_event("fatal")
                except Exception:
                    # Never crash the monitor
                    try:
                        self._emit_health_event("fatal")
                    except Exception:
                        pass
                    break

        import threading as _threading
        t = _threading.Thread(target=monitor, daemon=True)
        t.start()

    # ---- public API ----
    def get_status(self) -> Dict[str, Any]:
        st = self._load_state()
        # Normalize state label
        mode = st.get("mode") or ("architect_mode" if st.get("active") else None)
        state = "error" if st.get("state") == "error" else (mode or ("active" if st.get("active") else "idle"))
        payload = {
            "state": state,
            "active": bool(st.get("active", False)),
            "mode": mode,
            "updated": st.get("updated") or self._now(),
            "listening": bool(st.get("listening", False)),
            "listen_port": st.get("listen_port"),
        }
        return payload

    def reactivate(self, mode: str = "architect_mode", listen_port: Optional[int] = None) -> Dict[str, Any]:
        mode = (mode or "architect_mode").strip().lower()
        if mode not in {"architect_mode", "observer_mode"}:
            mode = "architect_mode"
        st = {"state": "active", "active": True, "mode": mode, "updated": self._now()}
        self._save_state(st)
        self._log_line(f"Reactivate requested: mode={mode}")
        try:
            log_event("genesis_reactivate", {"mode": mode})
        except Exception:
            pass
        # If a listen port is provided, start the intake listener
        if isinstance(listen_port, int) and listen_port > 0:
            try:
                self.listen(listen_port)
                st = self._load_state()
            except Exception:
                # keep activation successful even if listener fails
                pass
        return {"ok": True, **st}

    def shutdown(self) -> Dict[str, Any]:
        st = self._load_state()
        st.update({"state": "idle", "active": False, "updated": self._now()})
        self._save_state(st)
        self._log_line("Shutdown requested")
        try:
            log_event("genesis_shutdown", {})
        except Exception:
            pass
        return {"ok": True, **st}

    def tail_logs(self, n: int = 20) -> List[str]:
        p = self._latest_log_path()
        if not p.exists():
            return []
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            return lines[-int(n):]
        except Exception:
            return []

    def listen(self, port: int) -> Dict[str, Any]:
        """Launch the lightweight FastAPI intake service on the given port.

        Spawns a background uvicorn process serving
        agents.architect_genesis.intake_service:app and updates the state file
        with listening information. Best-effort; does not raise on failure.
        """
        try:
            p = int(port)
            if p <= 0 or p > 65535:
                raise ValueError("invalid_port")
        except Exception:
            self._log_line(f"Listener not started: invalid port {port}")
            return {"ok": False, "error": "invalid_port"}

        # If a previous PID exists, do not start another (best-effort)
        if self._listener_pid_path.exists():
            try:
                prev = int(self._listener_pid_path.read_text(encoding="utf-8").strip())
            except Exception:
                prev = None  # type: ignore
        else:
            prev = None  # type: ignore

        # Build environment with repo paths for module resolution
        env = os.environ.copy()
        py_paths = [str(self.repo_root), str(self.repo_root / "src")]
        env["PYTHONPATH"] = (env.get("PYTHONPATH") + os.pathsep if env.get("PYTHONPATH") else "") + os.pathsep.join(py_paths)

        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "agents.architect_genesis.api:app", "--host", "0.0.0.0", "--port", str(p)],
                cwd=str(self.repo_root),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Persist PID and state
            try:
                self._listener_pid_path.write_text(str(proc.pid), encoding="utf-8")
            except Exception:
                pass
            st = self._load_state()
            st.update({"listening": True, "listen_port": p, "updated": self._now()})
            self._save_state(st)
            # Update in-memory flags for health monitor
            self.listener_port = p
            self.listener_active = True
            self._log_line(f"[Genesis] Listening on port {p}")
            try:
                log_event("genesis_listen", {"port": p, "pid": proc.pid})
            except Exception:
                pass
            # Start health monitor (best-effort)
            try:
                self._start_health_monitor()
            except Exception:
                self._log_line("[Health] Monitor failed to start (non-fatal)")
            return {"ok": True, **st}
        except Exception as e:
            self._log_line(f"Listener failed to start on port {port}: {e}")
            try:
                log_event("genesis_listen_error", {"port": port, "error": str(e)})
            except Exception:
                pass
            return {"ok": False, "error": str(e)}

# --- Setup Project Root Path ---
from tools.charter_tools import search_knowledge_base
from tools.search_tools import search_tool

def main():
    """
    Main function to run the Ultimate Genesis Architect Crew.
    """
    # --- 0. Setup Environment ---
    dotenv_path = find_dotenv(filename=".env", usecwd=True) or (PROJECT_ROOT / ".env")
    if dotenv_path:
        load_dotenv(dotenv_path)

    # --- Env key mapping for robustness between Google/Gemini ---
    # Ensure both GEMINI_API_KEY and GOOGLE_API_KEY are available when only one is set.
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

    # --- Resilient LLM Initialization without unsupported probe calls ---
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    # Choose worker model by available keys (preference: Groq → Gemini → OpenAI)
    if has_groq:
        worker_model = "groq/llama3-70b-8192"
        print("Using Groq as the primary worker LLM.")
    elif has_gemini:
        worker_model = "gemini/gemini-2.5-flash"
        print("Using Gemini Flash as the primary worker LLM.")
    elif has_openai:
        worker_model = "openai/gpt-4o-mini"
        print("Using OpenAI as the primary worker LLM.")
    else:
        raise RuntimeError(
            "No supported LLM API keys found. Set GROQ_API_KEY, GEMINI_API_KEY/GOOGLE_API_KEY, or OPENAI_API_KEY."
        )

    llm = LLM(model=worker_model, temperature=0.2)

    # Manager LLM preference (Gemini Pro if available, else OpenAI, else Groq)
    if has_gemini:
        manager_model = "gemini/gemini-2.5-pro"
    elif has_openai:
        manager_model = "openai/gpt-4-turbo"
    elif has_groq:
        manager_model = "groq/llama3-70b-8192"
    else:
        manager_model = worker_model  # Should be unreachable due to earlier check

    manager_llm = LLM(model=manager_model, temperature=0.2)

    # --- 1. DEFINE AGENTS ---
    knowledge_seeker = Agent(
        role="Senior AI Research Analyst",
        goal="Conduct comprehensive research to inform the creation of a new agentic crew based on the user's request.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_knowledge_seeker.md").read_text(encoding="utf-8"),
        tools=[search_knowledge_base, search_tool],
        llm=llm,
        verbose=True,
    )

    charter_agent = Agent(
        role="Principal Solutions Architect",
        goal="Create a detailed, structured Project Charter for a new agentic crew based on provided research.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_charter_agent.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    code_architect_agent = Agent(
        role="Lead Agent Engineer",
        goal="Take a Project Charter and write the complete, production-ready Python code for the new CrewAI agent crew.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_code_architect.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    critic_agent = Agent(
        role="Principal Quality Assurance Engineer",
        goal="Review the Project Charter and the generated Python code to ensure they are aligned, complete, and adhere to all best practices.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_critic_agent.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    manager_agent = Agent(
        role="Genesis Crew Manager",
        goal="Orchestrate the research, planning, coding, and critique process to build a new agentic crew. Ensure the final deliverable is a high-quality, runnable Python script that meets the user's goal.",
        backstory="You are the master architect of the Agent Factory. You manage your expert team to ensure a flawless execution from concept to code.",
        llm=manager_llm,
        verbose=True
    )

    # --- 2. DEFINE TASKS ---
    print("--- Welcome to the Ultimate Genesis Architect ---")
    # Allow non-interactive runs via env var or CLI arg
    user_goal = os.getenv("GENESIS_USER_GOAL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not user_goal:
        user_goal = input("What kind of agentic crew would you like to build today?\n> ")

    # --- Dynamic Oversight: evaluate risk before action (Reflective L3) ---
    try:
        import importlib
        fw = importlib.import_module('agent_factory.utils.firewall_protocol')
        eval_fn = getattr(fw, 'evaluate_risk_before_action', None)
        if callable(eval_fn):
            # Allow callers to influence via env (default medium/internal)
            criticality = os.getenv('GENESIS_TASK_CRITICALITY', 'medium')
            sensitivity = os.getenv('GENESIS_DATA_SENSITIVITY', 'internal')
            risk = eval_fn({
                'goal': user_goal,
                'action': 'genesis_kickoff',
                'actor': 'GenesisCrew',
                'llm_confidence': None,
                'criticality': criticality,
                'sensitivity': sensitivity,
            })
            try:
                log_event('genesis_risk_attached', {'risk': risk})
            except Exception:
                pass
    except Exception:
        pass

    research_task = Task(
        description=f"Conduct thorough research on the user's goal: '{user_goal}'. First, search the internal knowledge base for best practices and templates. If needed, use the web search tool to find modern, external examples and architectural patterns.",
        expected_output="A markdown research brief summarizing findings, including internal best practices and external examples relevant to the user's goal.",
        agent=knowledge_seeker,
    )

    charter_task = Task(
        description="Using the research brief, create a comprehensive Project Charter for the new agent crew. The charter must be detailed and follow the standard template.",
        expected_output="A complete Project Charter in markdown format.",
        agent=charter_agent,
        context=[research_task],
    )

    code_task = Task(
        description="Based ONLY on the Project Charter provided, write the complete, runnable Python script for the new agent crew. Do not use any other examples.",
        expected_output="A single Python code block containing the full CrewAI script.",
        agent=code_architect_agent,
        context=[charter_task],
    )

    critique_task = Task(
        description="Review the Project Charter and the generated Python code. Check for alignment, completeness, and adherence to our best practices. Provide actionable feedback or approve the code.",
        expected_output="Either the original Python code block if it is perfect, or a list of required changes.",
        agent=critic_agent,
        context=[charter_task, code_task],
    )

    report_task = Task(
        description="Compile the final report. Review the critique and the code. If the critique required changes, ask the Lead Agent Engineer to rewrite the code incorporating the feedback. The final output MUST be only the finished, approved Python code block.",
        expected_output="The final, complete, runnable Python code block for the new agent crew.",
        agent=manager_agent,
        context=[critique_task, code_task],
    )

    # --- 3. CREATE AND RUN THE CREW ---
    genesis_crew = Crew(
        agents=[knowledge_seeker, charter_agent, code_architect_agent, critic_agent],
        tasks=[research_task, charter_task, code_task, critique_task, report_task],
        process=Process.hierarchical,
        manager_agent=manager_agent,
        verbose=True,
    )

    print("\n--- Ultimate Genesis Crew is now building your new agent crew... ---")

    # Audit + Procedural trace
    log_agent_run(agent_name="GenesisCrew", task_id="kickoff", status="started")
    from agent_factory.utils.procedural_memory_pg import trace_run as _trace_run  # local import to avoid cycles
    result = None
    try:
        with _trace_run("GenesisCrew", task="kickoff") as trace:
            # Attach last computed risk from earlier step if available via env cache (best-effort)
            try:
                import importlib
                fw = importlib.import_module('utils.firewall_protocol')
                eval_fn = getattr(fw, 'evaluate_risk_before_action', None)
                if callable(eval_fn):
                    criticality = os.getenv('GENESIS_TASK_CRITICALITY', 'medium')
                    sensitivity = os.getenv('GENESIS_DATA_SENSITIVITY', 'internal')
                    risk_payload = eval_fn({
                        'goal': user_goal,
                        'action': 'genesis_kickoff',
                        'actor': 'GenesisCrew',
                        'llm_confidence': None,
                        'criticality': criticality,
                        'sensitivity': sensitivity,
                    })
                    trace["risk"] = risk_payload
            except Exception:
                pass
            result = genesis_crew.kickoff()
            trace["status"] = "success"
        log_agent_run(agent_name="GenesisCrew", task_id="kickoff", status="success")
    except Exception as e:
        log_agent_run(agent_name="GenesisCrew", task_id="kickoff", status="failed")
        raise

    # Human-on/in-the-loop approval before revealing final output
    if os.getenv("HITL_APPROVE", "false").lower() != "true":
        try:
            resp = input("Review output above (internal). Type 'approve' to continue: ")
            if resp.strip().lower() != "approve":
                print("Operation not approved. Exiting without printing final result.")
                return
        except EOFError:
            print("No approval input available; aborting output under HITL policy.")
            return

    print("\n--- Genesis Crew Work Complete ---")
    print("Final Result:")
    print(result)

if __name__ == "__main__":
    # Autostart FastAPI listener for Genesis on port 5055
    import uvicorn  # type: ignore
    from agents.architect_genesis.api import app  # lazy import to avoid circulars
    uvicorn.run(app, host="0.0.0.0", port=5055, log_level="info")
