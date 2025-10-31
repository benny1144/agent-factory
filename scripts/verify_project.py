from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from utils.paths import (
    PROJECT_ROOT,
    LOGS_DIR,
    TASKS_DIR,
    TASKS_COMPLETE_DIR,
    POLICIES_DIR,
)
from tools.logging_utils import JsonlLogger


@dataclass
class Check:
    name: str
    passed: bool
    info: str = ""


SYSTEM_VERIFICATION_LOG = LOGS_DIR / "system_verification.jsonl"


def _log_check(logger: JsonlLogger, check: Check) -> None:
    try:
        logger.log(
            ok=check.passed,
            data={
                "component": "phase_0_verification",
                "check": check.name,
                "info": check.info,
            },
        )
    except Exception:
        # Do not fail verification on logging issues
        pass


def check_exists(path: Path, name: str) -> Check:
    return Check(name=name, passed=path.exists(), info=str(path.relative_to(PROJECT_ROOT)) if path.exists() else f"missing: {path}")


def check_file_contains(path: Path, substrings: List[str], name: str) -> Check:
    if not path.exists():
        return Check(name=name, passed=False, info=f"missing: {path}")
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing: List[str] = [s for s in substrings if s not in text]
        if missing:
            return Check(name=name, passed=False, info=f"missing substrings: {missing}")
        return Check(name=name, passed=True, info="ok")
    except Exception as e:
        return Check(name=name, passed=False, info=f"error reading: {e}")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_file_if_missing(path: Path, content: str) -> bool:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    return False


def _parse_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def _extract_yaml_api_key(yaml_path: Path, service: str) -> str | None:
    """Very light-weight YAML scanner to find llm_integrations.<service>.api_key.
    Avoids adding PyYAML; relies on indentation present in our file.
    """
    if not yaml_path.exists():
        return None
    current = None
    in_llm = False
    for raw in yaml_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if not in_llm:
            if line.strip().startswith("llm_integrations:"):
                in_llm = True
            continue
        # detect new service
        if line.startswith("  ") and line.strip().endswith(":") and not line.strip().startswith("#"):
            current = line.strip().rstrip(":")
            continue
        # capture api_key for the desired service
        if current == service and "api_key:" in line:
            # expect pattern like: "    api_key: <value>"
            try:
                value = line.split(":", 1)[1].strip()
                value = value.strip('"').strip("'") if value else ""
                return value or None
            except Exception:
                return None
        # exit llm block if dedented
        if line and not line.startswith("  ") and in_llm:
            break
    return None


def collect_checks() -> Tuple[List[Check], List[str]]:
    checks: List[Check] = []
    errors: List[str] = []

    sys_logger = JsonlLogger(log_file=SYSTEM_VERIFICATION_LOG)

    # Subtask 0.1 — Verify/Create Core Directories
    core_dirs = [
        (PROJECT_ROOT / "governance", "governance dir"),
        (LOGS_DIR, "logs dir"),
        (TASKS_DIR, "tasks dir"),
        (PROJECT_ROOT / "frontend", "frontend dir"),
        (PROJECT_ROOT / "factory_agents", "factory_agents dir"),
        (PROJECT_ROOT / "knowledge_base", "knowledge_base dir"),
        # previously verified
        (PROJECT_ROOT / "utils", "utils dir"),
        (PROJECT_ROOT / "tools", "tools dir"),
        (PROJECT_ROOT / "scripts", "scripts dir"),
        (PROJECT_ROOT / "tests", "tests dir (optional)"),
        (TASKS_COMPLETE_DIR, "tasks_complete dir"),
        (POLICIES_DIR, "governance/policies dir"),
    ]

    for p, label in core_dirs:
        try:
            _ensure_dir(p)
        except Exception as e:
            # record inability to create but continue
            checks.append(Check(name=f"create: {label}", passed=False, info=str(e)))
            _log_check(sys_logger, checks[-1])
        c = check_exists(p, f"exists: {label}")
        checks.append(c)
        if not c.passed and label in {"utils dir", "tools dir", "scripts dir", "logs dir", "tasks dir", "governance dir", "governance/policies dir"}:
            errors.append(f"Missing required directory: {p}")
        _log_check(sys_logger, c)

    # Subtask 0.2 — Baseline Governance Check (ensure files; create templates if missing)
    ethical_yaml = PROJECT_ROOT / "governance" / "ethical_drift_monitor.yaml"
    federation_yaml = PROJECT_ROOT / "governance" / "federation_policies.yaml"
    compliance_kernel_py = PROJECT_ROOT / "compliance" / "compliance_kernel.py"

    created_flags = {
        "ethical_drift_monitor.yaml": _write_file_if_missing(
            ethical_yaml,
            content=(
                "# Ethical Drift Monitor Configuration\n"
                "version: 1\n"
                "thresholds:\n"
                "  semantic: 0.05\n"
                "  ethical: 0.12\n"
                "logging:\n"
                "  enabled: true\n"
                "  path: logs/ethical_drift_alerts.jsonl\n"
            ),
        ),
        "federation_policies.yaml": _write_file_if_missing(
            federation_yaml,
            content=(
                "# Federation Policies\n"
                "version: 1\n"
                "agents:\n"
                "  allow_external_network: false\n"
                "  default_ttl_seconds: 86400\n"
                "audit:\n"
                "  enabled: true\n"
            ),
        ),
        "compliance_kernel.py": _write_file_if_missing(
            compliance_kernel_py,
            content=(
                "from __future__ import annotations\n\n"
                "\"\"\"Compliance Kernel Stub\n\n"
                "Exposes minimal interfaces for audit logging and policy checks.\n"
                "This is a generated template and should be extended per governance.\n"
                "\"\"\"\n\n"
                "from pathlib import Path\n"
                "from typing import Dict, Any\n\n"
                "from utils.paths import LOGS_DIR\n"
                "from tools.logging_utils import JsonlLogger\n\n"
                "_logger = JsonlLogger(log_file=LOGS_DIR / 'audit.jsonl')\n\n"
                "def record_audit(event: str, data: Dict[str, Any] | None = None) -> None:\n"
                "    _logger.log(True, {\"component\": \"compliance_kernel\", \"event\": event, \"data\": data or {}})\n\n"
                "def check_policy(name: str, context: Dict[str, Any] | None = None) -> bool:\n"
                "    # Always allow by default in template\n"
                "    record_audit('policy_check', {\"name\": name, \"allowed\": True})\n"
                "    return True\n"
            ),
        ),
    }

    for fname, created in created_flags.items():
        c = Check(name=f"ensure file: {fname}", passed=True, info=("created" if created else "exists"))
        checks.append(c)
        _log_check(sys_logger, c)

    # Subtask 0.3 — Environment Validation (.env vs factory_config/api_keys.yaml)
    env_path = PROJECT_ROOT / ".env"
    env_vars = _parse_env(env_path)
    yaml_path = PROJECT_ROOT / "factory_config" / "api_keys.yaml"

    services = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
    }

    for service, env_key in services.items():
        env_present = env_key in env_vars and bool(env_vars.get(env_key))
        yaml_key = _extract_yaml_api_key(yaml_path, service)
        yaml_present = yaml_key is not None and yaml_key != ""
        matches = False
        if env_present and yaml_present:
            matches = (env_vars.get(env_key) == yaml_key)
        # Presence check
        c1 = Check(name=f"env presence: {service}", passed=env_present, info=env_key + (" present" if env_present else " missing"))
        checks.append(c1)
        _log_check(sys_logger, c1)
        # YAML presence
        c2 = Check(name=f"yaml presence: {service}", passed=yaml_present, info=("present" if yaml_present else "missing"))
        checks.append(c2)
        _log_check(sys_logger, c2)
        # Match check (non-fatal)
        c3 = Check(name=f"env/yaml match: {service}", passed=matches, info=("match" if matches else "mismatch or insufficient data"))
        checks.append(c3)
        _log_check(sys_logger, c3)
        # Do not append to errors for env mismatches to keep verification non-blocking

    # Subtask 0.4 — Log Verification Report already covered via logger per-check

    # Key files from original verification
    key_files = [
        (PROJECT_ROOT / "README.md", "README.md"),
        (PROJECT_ROOT / "pyproject.toml", "pyproject.toml"),
        (PROJECT_ROOT / "requirements.txt", "requirements.txt"),
        (TASKS_DIR / "AgentFactory_MasterBuild_Phase0_35.json", "tasks json"),
        (POLICIES_DIR / "junie_execution_policy.yaml", "execution policy"),
        (PROJECT_ROOT / "utils" / "paths.py", "utils/paths.py"),
    ]
    for p, label in key_files:
        c = check_exists(p, f"exists: {label}")
        checks.append(c)
        if not c.passed:
            errors.append(f"Missing required file: {p}")
        _log_check(sys_logger, c)

    # Policy sanity
    policy_yaml = POLICIES_DIR / "junie_execution_policy.yaml"
    if policy_yaml.exists():
        c = check_file_contains(policy_yaml, ["policy_id:", "auto_approval:", "execution_mode:"], "policy sanity")
        checks.append(c)
        if not c.passed:
            errors.append("Policy file missing required keys.")
        _log_check(sys_logger, c)

    # Ensure logs dir writable
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = LOGS_DIR / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        c = Check(name="logs writable", passed=True, info=str(LOGS_DIR.relative_to(PROJECT_ROOT)))
        checks.append(c)
        _log_check(sys_logger, c)
    except Exception as e:
        c = Check(name="logs writable", passed=False, info=str(e))
        checks.append(c)
        _log_check(sys_logger, c)
        errors.append(f"Logs dir not writable: {e}")

    return checks, errors


def verify_project() -> Dict[str, Any]:
    """Run Phase 0 verification checks (extended per MasterBuild Phase 0).

    Returns:
        dict with keys: ok, checks (list of dict), errors (list of str)
    """
    checks, errors = collect_checks()
    # Consider only hard errors (missing critical dirs/files, log writability)
    ok = len([c for c in checks if c.passed]) == len(checks) or not errors
    return {
        "ok": ok,
        "checks": [asdict(c) for c in checks],
        "errors": errors,
    }


def _main(argv: List[str]) -> int:
    report = verify_project()
    print(json.dumps(report, indent=2))
    # Return non-zero only on hard errors
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
