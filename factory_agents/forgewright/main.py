from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Ensure repo root on path
import tools.startup  # noqa: F401
from utils.paths import PROJECT_ROOT, TOOLS_DIR, TESTS_DIR
from agents.model_router import ModelRouter

PERSONA_YAML = PROJECT_ROOT / "factory_agents" / "forgewright" / "persona_forgewright.yaml"


def _load_persona() -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(PERSONA_YAML.read_text(encoding="utf-8"))
    except Exception:
        return {
            "name": "Forgewright",
            "role": "Federation Toolmaker",
            "models": {"primary": "gpt-5-mini", "fallback": "oss-safeguard"},
        }


def main() -> int:
    """Forgewright (Toolmaker) — routes all LLM calls via ModelRouter.

    Interactive: prompts for a short tool concept and emits a stub file for demo purposes.
    All model usage is logged to logs/compliance/model_usage.jsonl and governance/event_bus.jsonl.
    """
    load_dotenv()
    persona = _load_persona()

    print("--- Forgewright — Federation Toolmaker ---")
    tool_name = input("Enter the tool's name (e.g., 'file_reader'): ").strip() or "forge_demo"
    tool_desc = input("Enter a one-sentence description: ").strip() or "Demo tool"

    # Route prompt via ModelRouter (primary: gpt-5-mini; fallback: oss-safeguard)
    router = ModelRouter(agent_name="Forgewright")
    prompt = (
        f"Create a minimal Python function for a tool named '{tool_name}'. "
        f"Description: {tool_desc}. Return only code in a single function with a docstring."
    )
    meta = {"risk": "low", "tokens": 1200, "task_id": f"fw-{tool_name}", "phase": "38.6"}
    res = router.route(meta, prompt)
    output = str(res.get("output") or "")

    # Very lightweight extraction: if code fenced, pick fence; else wrap as function
    code = output
    try:
        import re
        m = re.search(r"```(?:python)?\n([\s\S]*?)```", output)
        if m:
            code = m.group(1).strip()
        if not code.strip().startswith("def "):
            code = f"def {tool_name}_tool():\n    \"\"\"{tool_desc}\"\"\"\n    return {json.dumps(tool_desc)}\n"
    except Exception:
        code = f"def {tool_name}_tool():\n    return {json.dumps(tool_desc)}\n"

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    tool_path = TOOLS_DIR / f"{tool_name}.py"
    tool_path.write_text(code, encoding="utf-8")
    print(f"[Forgewright] Wrote {tool_path}")

    # Minimal smoke test file
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    tpath = TESTS_DIR / f"test_{tool_name}.py"
    if not tpath.exists():
        tpath.write_text(
            """def test_module_compiles():\n    import importlib.util, pathlib\n    p = pathlib.Path(r'%s')\n    spec = importlib.util.spec_from_file_location('x', str(p))\n    mod = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(mod)  # type: ignore\n    assert True\n""" % str(tool_path),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
