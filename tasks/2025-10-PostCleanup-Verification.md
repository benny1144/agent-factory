[JUNIE TASK]
Title: Post-Cleanup Verification & Certification
Preconditions:
- Repo: benny1144/agent-factory
- Branch: main or maintenance/verified_<timestamp>
- All previous cleanup tasks completed and committed
  Plan:
1. **Comprehensive Audit Sweep**
    - Scan /tasks/, /agents/, /tools/, /governance/, /logs/ for new or modified files since last audit hash.
    - Compute SHA-256 for each and record to /compliance/audit_log/integrity_snapshot_<timestamp>.csv.
    - Run python tools/governance_check.py --deep and capture output to /reports/governance_audit_<timestamp>.md.

2. **Phase-wide Verification**
    - Reconstruct timeline from compliance/audit_log/junie_activity.csv.
    - Cross-validate timestamps and commits for Phase 0→Phase 3 (Foundation → Genesis Architect).
    - Verify that each task has a passing status and corresponding commit hash.
    - Produce /reports/phase_audit_summary_<timestamp>.md.

3. **Cleanup of Residuals**
    - Remove /logs/archive/ files older than 60 days.
    - Prune /backups/ bundles older than 3 months (retain last 2 snapshots).
    - Delete temporary branches maintenance/preflight_* and fix/import-paths after merge.

4. **Certification Generation**
    - Generate /reports/factory_certification_<timestamp>.json containing:
      {
      "phase": "Post-Cleanup",
      "certified_by": "Junie",
      "supervised_by": "HITL-<your-user>",
      "compliance_score": "<auto-computed>",
      "timestamp": "<UTC>"
      }
    - Append summary line to /compliance/audit_log/factory_certification.csv.

5. **Optional Extended Sanity Checks**
    - Run pytest --maxfail=1 --disable-warnings.
    - Run python tools/charter_tools.py --status to confirm vector memory sync.
    - Verify that Archivist and Genesis both start and register under /governance/agents_registry.yaml.

Verification:
- integrity_snapshot file exists and matches current commit hash.
- governance_audit and phase_audit_summary both report "0 anomalies".
- certification JSON produced and logged in audit CSV.
  Rollback:
- Restore previous snapshot bundle from /backups/ if integrity diff > 0 changes flagged.
- Revert to last passing commit using git revert <hash>.
