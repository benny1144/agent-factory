# Agent Factory — Junie Project Guidelines

These guidelines instruct **Junie (JetBrains AI Implementor)** how to work inside this repo.
They define *how to create/edit code, files, and folders* while respecting our governance (Human Firewall), standards, and directory layout.

---

## 1) Project Overview

- **Mission:** Build and evolve a multi-agent “Agent Factory” with:
  - **Genesis** (architect & code generator),
  - **Toolmaker’s Copilot** (tool scaffolding),
  - **Knowledge Curator** (RAG pipeline),
  - **Prometheus** (R&D/optimization; Phase 3).
- **Primary language:** Python 3.11+
- **Core libs:** CrewAI (+ tools), LangChain/LCEL (selectively), FAISS or alternative vector stores, Google/ OpenAI/ Anthropic LLMs.
- **IDE:** IntelliJ IDEA (Python plugin) or PyCharm.

---

## 2) Directory Layout (expected)

```

agents/
architect_genesis/
main.py
requirements.txt
toolmaker_copilot/
main.py
requirements.txt
knowledge_curator/
curate.py
requirements.txt
personas/
genesis_*.md
toolmaker_copilot.md
tools/
charter_tools.py          # search_knowledge_base(), etc.
search_tools.py           # serper search, etc.
file_tools.py
test_api_keys.py
knowledge_base/
source_documents/
vector_store/
faiss_index/
utils/
paths.py                  # (may be added)
procedural_memory.py      # (may be added)
procedural_memory_pg.py   # (may be added)
README.md
GOVERNANCE.md

```

> If any items are missing when a task requires them, **create them** following these conventions.

---

## 3) Junie’s Execution Protocol (always follow)

When I (Junie) receive a task in this project:

1. **Plan (Dry-Run):**  
   - Outline the steps, files to touch/create, and side-effects (tests, embeddings, DB).
   - Ask for confirmation *if* the plan changes architecture, dependencies, or governance rules.  
   - Otherwise proceed.

2. **Create/Edit Safely:**  
   - Use absolute, repo-root-aware paths via `utils/paths.py` (if present).  
   - Never hardcode `../../` relative paths when reading personas/knowledge.

3. **Validate:**  
   - Run IDE inspections, basic lint (`ruff` if configured), and quick import checks.
   - For Python scripts with `__main__`, run a smoke execution *only when safe* (no network unless explicitly allowed).

4. **Log changes:**  
   - Summarize created/edited files (paths + short diff overview).
   - Note any TODOs or follow-ups.

5. **Respect Governance:**  
   - Follow Human Firewall rules (see §8 Security & Safety).

---

## 4) Coding Standards

- **Python:** 3.11+, typing required where practical (`from __future__ import annotations`).
- **Style:** PEP8; prefer Black/ Ruff defaults if configured.
- **Docstrings:** Google or NumPy style. Public functions/classes must explain inputs/outputs and failure modes.
- **Logging:** Use `logging` (INFO for normal ops, DEBUG for dev). Prefer JSON logs if configured later.
- **Errors:** Raise precise exceptions; do not swallow traces. Validate inputs and tool I/O schemas.
- **Determinism:** Avoid global side-effects; make paths configurable via env or CLI flags.

---

## 5) Agent Patterns (CrewAI)

- **Hierarchy:** Prefer manager (stronger model) orchestrating worker agents for complex tasks.
- **Roles:** Keep *Knowledge Seeker → Charter → Code Architect → Critic* separation for Genesis.
- **Models:** Use high-reasoning model for manager; cost-effective for workers. Keep temperature low for deterministic tasks.
- **Outputs:** When producing code/artifacts, **also return a machine-readable block** (JSON or fenced code) suitable for saving by procedural memory (see §7).

---

## 6) Tooling Conventions

- **Naming alignment:** Tool names in personas must match actual functions.
  - e.g., use `search_knowledge_base` and `search_tool` (not `knowledge_base_search`).
- **I/O envelope (standard):**
  ```json
  {
    "ok": true,
    "data": { ... },        // payload
    "error": null,          // or string
    "meta": { "source": "...", "duration_ms": 123 }
  }
  ```

* **File access:** Use helpers from `tools/file_tools.py` where present.
* **Web search:** Centralize via `tools/search_tools.py`.
* **Key tests:** `tools/test_api_keys.py` should validate basic connectivity; do not ship secrets.

---

## 7) Procedural Memory (Step 2.2)

* **Goal:** Save “supervised execution” results (e.g., Genesis final approved code) with the initiating goal.
* **Default sink:** `data/procedural_memory/skills.jsonl`

  * Record schema:

    ```json
    {
      "ts": "2025-01-01T00:00:00Z",
      "user_goal": "string",
      "artifact_type": "genesis_crew_python",
      "artifact_lang": "python",
      "artifact": "code string",
      "meta": { "worker_model": "...", "manager_model": "...", "repo_commit": "..." }
    }
    ```
* **Optional sink:** Postgres table `procedural_skills` if `PG*` env vars are set.
* **When to log:** After a successful `genesis_crew.kickoff()` or Prometheus brief generation.
* **Never** log API keys, tokens, or user PII.

---

## 8) Security & Safety (Human Firewall)

* **No secrets in code.** Read from env (`.env` locally, secrets manager in CI).
* **Network:** Only call external services through approved tools; document endpoints used.
* **Deserialization:** `FAISS.load_local(..., allow_dangerous_deserialization=True)` is allowed **only** for our own vetted artifacts. Prefer rebuilding index from `knowledge_base/source_documents` in CI.
* **Data boundaries:** Do not exfiltrate source documents or internal prompts to third-party APIs unless explicitly approved.
* **Approvals:** Any change that adds dependencies, opens network paths, or modifies governance requires explicit confirmation in the PR description.

---

## 9) Knowledge Base (RAG)

* **Embeddings:** Prefer `text-embedding-004` (or successor) for consistency.
* **Indexing:** Source from `knowledge_base/source_documents/*`; write to `knowledge_base/vector_store/faiss_index/`.
* **Rebuild:** Provide a deterministic script or `make embed` target. Produce a manifest of indexed files + hash.

---

## 10) Paths & Portability

* Prefer a shared `utils/paths.py`:

  ```python
  from pathlib import Path
  PROJECT_ROOT = Path(__file__).resolve().parents[1]  # adjust if placed in utils/
  PERSONAS_DIR = PROJECT_ROOT / "personas"
  KB_SRC_DIR = PROJECT_ROOT / "knowledge_base" / "source_documents"
  KB_INDEX_DIR = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss_index"
  ```
* Do **not** rely on CWD; always resolve from `PROJECT_ROOT`.

---

## 11) Testing & CI (lightweight)

* **Unit tests:** Add minimal `pytest` tests for any new tool or deterministic function (happy path + one failure case).
* **Smoke scripts:** For agents with `__main__`, allow running with a sample goal via env (e.g., `GENESIS_USER_GOAL`).
* **CI (if configured):**

  * Lint (`ruff`), optional types (`pyright`).
  * Rebuild FAISS from sources to detect drift.
  * Prohibit committing secrets.

---

## 12) Commits & PRs

* **Conventional Commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
* **PR template (expectation):**

  * Problem → Solution → Risk/Security notes → Test evidence → Screenshots/logs → Rollback plan.

---

## 13) How to Ask Junie for Work (Prompt Patterns)

* **Create a new tool**

  > “Create `tools/<name>.py` implementing function `<fn>` with the standard I/O envelope. Add docstring with usage, minimal `pytest` in `tests/test_<name>.py` (happy + error). Export via `__all__`. Update any persona/tool registry as needed. Summarize changes.”

* **Add a new agent/crew**

  > “Under `agents/<agent_name>/`, scaffold `main.py` with a CrewAI crew (sequential), tasks X→Y→Z, models: worker=`gemini-2.5-flash`, manager=`gemini-2.5-pro`. Read personas from `personas/`. Include `if __name__ == '__main__'` CLI: `--goal`, `--kb`. Provide run instructions.”

* **Wire procedural memory**

  > “After successful run, append to `data/procedural_memory/skills.jsonl` per §7. If `PG*` env set, also insert into `procedural_skills`.”

* **Refactor for path safety**

  > “Replace relative path literals with `utils/paths.py` helpers per §10. Add module if missing.”

* **KB update**

  > “Add a source file to `knowledge_base/source_documents/` and rebuild FAISS index deterministically. Log manifest.”

---

## 14) What Junie Must Never Do

* Commit secrets or API keys.
* Delete knowledge base sources or procedural logs without explicit instruction.
* Change governance rules without explicit instruction.
* Introduce unreviewed network calls or telemetry.

---

*End of guidelines.*
