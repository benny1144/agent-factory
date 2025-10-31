2025-10 Agent Factory Cleanup & Standardization Roadmap

Purpose:
Stabilize repository architecture, align environments, unify logs, enforce governance consistency, and prepare for multi-agent expansion (Archivist, Genesis, Junie).

[JUNIE TASK]

Title: 1. Pre-Flight Repository & Governance Validation
Preconditions:

Branch: main or dev clean (no uncommitted changes)

Repo: benny1144/agent-factory

Genesis and Archivist idle (no active builds)

Plan:

Branch Safety

Run git status and ensure working directory is clean.

If changes exist, commit them with message pre-flight checkpoint.

Create temporary branch maintenance/preflight_<timestamp>.

Backup Snapshot

Archive current repo state:

git bundle create ./backups/preflight_<timestamp>.bundle --all


Verify bundle integrity (git verify-bundle).

Governance Sanity Check

Run python tools/firewall_admin.py --validate

Run python tools/governance_check.py --validate

Confirm all agents listed in /governance/agents_registry.yaml.

Environment Verification

Confirm active Python version ≥ 3.11

Confirm venv active and pip check passes

Run quick dependency audit:

pip list --outdated


Log result to /reports/environment_audit_<timestamp>.txt.

Audit & Log Preparation

Ensure /compliance/audit_log/junie_activity.csv exists; if not, create header.

Rotate /logs/ to /logs/archive/<timestamp>/ and start fresh.

Human Firewall Confirmation (Optional)

Prompt for human confirmation flag (HITL) before executing cleanup roadmap.

Only proceed if user flag confirm_cleanup = true set in /config/human_firewall.yaml.

Verification:

Backup bundle exists and passes integrity check.

Governance validators report “OK”.

Environment audit report generated.

Rollback:

Checkout backup bundle or revert branch:

git checkout main
git reset --hard HEAD~1
git restore .
git bundle unbundle ./backups/preflight_<timestamp>.bundle

[JUNIE TASK]

Title: 2. Environment Harmonization and Dependency Lock
Plan:

Aggregate all requirements.txt files under /agents/ and /src/.

Merge into /environment/requirements_master.txt.

Generate pinned lock via pip-compile or poetry lock.

Remove duplicate or obsolete dependencies.

Verify venv build installs cleanly.
Verification:
pytest smoke passes on clean venv.
Rollback: Restore individual requirements.txt from backup.

[JUNIE TASK]

Title: 3. Configuration Consolidation
Plan:

Move all .env files to /config/.env.

Add tools/config_loader.py to load validated envs.

Replace any dotenv calls with unified loader.

Confirm all API keys pulled from Vault / Secret Manager.
Verification: Agents boot with single configuration source.

[JUNIE TASK]

Title: 4. Unified Logging & Audit Pipeline
Plan:

Create /tools/log_utils.py for JSONL logging.

Route log_event() and trace_run() through this interface.

Standardize /logs/<agent_name>_<date>.jsonl format.

Auto-rotate logs >10 MB.

Index all new logs in /compliance/audit_log/.
Verification: Logs visible and validated by Governance Kernel.

[JUNIE TASK]

Title: 5. CI Pipeline Initialization
Plan:

Create .github/workflows/test.yml.

Run pytest + black + flake8 + mypy.

Require coverage ≥ 80%.

Archive results under /reports/ci/.
Verification: CI passes on push.

[JUNIE TASK]

Title: 6. Code Quality Sweep
Plan:

Apply black (line-length 100), isort, and autoflake.

Remove unused imports and debug prints.

Add .pre-commit-config.yaml.
Verification: pre-commit run --all-files passes.

[JUNIE TASK]

Title: 7. Governance Kernel Standardization
Plan:

Audit /governance/ YAML configs.

Merge fragmented registry, firewall, ethical_drift.

Add governance_check.py schema validator.

Enforce automatic agent registration on boot.
Verification: python tools/governance_check.py --validate returns OK.

[JUNIE TASK]

Title: 8. Reflective Sync & Vector Index Optimization
Plan:

Move embedding logic to /src/memory_engine.py.

Add vector compaction and metadata tagging.

Log each sync in /compliance/audit_log/reflective_sync.csv.
Verification: Sync completes with 0 errors.

[JUNIE TASK]

Title: 9. Inter-Agent Communication Layer (IACL)
Plan:

Create /tools/iacl.py defining message envelope {sender, target, action, payload, timestamp}.

Replace file polling with lightweight message queue.

Add test stubs for multi-agent interactions.
Verification: Archivist ↔ Genesis ↔ Junie message round-trip passes.

[JUNIE TASK]

Title: 10. Documentation & Developer Portal Refresh
Plan:

Generate API docs with MkDocs or PDoc to /docs/api/.

Create /README.md templates for all agents.

Add “Quick Start” scripts: run_genesis.ps1, run_archivist.ps1.

Include Mermaid architecture diagram.
Verification: mkdocs build passes and docs open locally.

Execution Mode: Sequential (Auto-Continue on Success, Pause on Error).
Rollback: Restore last passing commit via git revert if any stage fails.