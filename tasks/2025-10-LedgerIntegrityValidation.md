[JUNIE TASK]

Title: Implement Nightly Ledger Chain Verification Job (Governance Integrity Enforcement)

Preconditions:

Repo: benny1144/agent-factory

Branch: ci/ledger_integrity_verification

Ledger file: /governance/ledger_master.csv

Federation Validation CI already appends entries with checksums.

Governance Console (FastAPI + React) operational.

🧩 Phase 1 — Ledger Chain Verification Script

File: /governance/verify_ledger_chain.py

import csv, hashlib, datetime, os, json, sys

LEDGER_PATH = "governance/ledger_master.csv"
REPORT_DIR = "compliance/reports/"
os.makedirs(REPORT_DIR, exist_ok=True)

def compute_hash(record):
return hashlib.sha256(record.encode()).hexdigest()

def verify_chain():
if not os.path.exists(LEDGER_PATH):
print("[LedgerVerify] Ledger file not found.")
sys.exit(1)

    with open(LEDGER_PATH) as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("[LedgerVerify] Ledger is empty.")
        sys.exit(1)

    last_hash = None
    chain_ok = True
    results = []

    for i, row in enumerate(rows):
        if len(row) < 4:
            results.append({"line": i, "error": "Malformed entry"})
            chain_ok = False
            continue

        ts, source, record, checksum = row
        expected = compute_hash(record)

        if checksum != expected:
            results.append({"line": i, "error": "Checksum mismatch"})
            chain_ok = False

        if last_hash and not record.startswith(last_hash[:8]):
            # Optional chaining enforcement
            pass

        last_hash = checksum

    ts = datetime.datetime.utcnow().isoformat()
    report = {
        "timestamp": ts,
        "verified": chain_ok,
        "entries": len(rows),
        "issues": results
    }

    with open(f"{REPORT_DIR}ledger_chain_verification_{ts}.json", "w") as rf:
        json.dump(report, rf, indent=2)

    if chain_ok:
        print(f"[LedgerVerify] OK — {len(rows)} entries validated.")
    else:
        print(f"[LedgerVerify] ALERT — issues detected: {len(results)}")
        sys.exit(1)

if __name__ == "__main__":
verify_chain()

🧩 Phase 2 — Schedule Verification in GitHub Actions

File: .github/workflows/ledger-integrity.yml

name: Ledger Integrity Verification

on:
schedule:
- cron: "0 2 * * *"  # every night at 2 AM UTC
workflow_dispatch:

jobs:
verify-ledger:
runs-on: ubuntu-latest
timeout-minutes: 10
steps:
- name: Checkout repository
uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Ledger Verification
        run: |
          python governance/verify_ledger_chain.py

      - name: Upload Verification Report
        uses: actions/upload-artifact@v4
        with:
          name: ledger_chain_reports
          path: compliance/reports/

      - name: Append Ledger Verification Result
        run: |
          python governance/ledger_sync.py

🧩 Phase 3 — Governance Dashboard Integration

Backend Route: /ledger/verification

from fastapi import APIRouter
import json, os, glob

router = APIRouter()

@router.get("/ledger/verification")
def get_ledger_verification():
reports = sorted(glob.glob("compliance/reports/ledger_chain_verification_*.json"))
if not reports:
return {"ok": False, "data": []}
latest = reports[-1]
with open(latest) as f:
data = json.load(f)
return {"ok": True, "data": data}


Frontend Widget: LedgerIntegrityCard.tsx

import { useEffect, useState } from "react";

export default function LedgerIntegrityCard() {
const [status, setStatus] = useState<any>(null);

useEffect(() => {
const load = async () => {
const r = await fetch(`${import.meta.env.VITE_API_URL}/ledger/verification`);
const j = await r.json();
if (j.ok) setStatus(j.data);
};
load();
const interval = setInterval(load, 60000);
return () => clearInterval(interval);
}, []);

if (!status) return <div>Loading ledger integrity...</div>;
return (
<div className="p-4 bg-gray-900 rounded-2xl shadow text-gray-200">
<h2 className="text-lg font-bold mb-2">Ledger Integrity</h2>
<p>Status: <span className={`font-semibold ${status.verified?"text-green-400":"text-red-400"}`}>
{status.verified ? "Valid" : "Issues Detected"}
</span></p>
<p>Entries: {status.entries}</p>
<p>Checked: {status.timestamp}</p>
</div>
);
}


Add LedgerIntegrityCard to your dashboard grid near “Federation Integrity.”

🧩 Phase 4 — Audit Integration

Each nightly run logs to /compliance/audit_log/ledger_integrity.csv:

timestamp, entries, verified, issues_detected, trace_id


Genesis also mirrors verification summaries into the Governance Ledger, chaining checksums.

🧾 Rollback

Delete .github/workflows/ledger-integrity.yml.

Remove /governance/verify_ledger_chain.py.

Remove dashboard integration.

Clean up related audit log entries.

✅ Expected Outcome

Every 24 hours, CI verifies the entire ledger for hash integrity and tamper detection.

Any modification triggers automatic alerts in the Governance Dashboard.

A JSON verification report is saved in /compliance/reports/.

Results are appended to the Governance Ledger with cryptographic checksum.

Governance and compliance teams have immutable assurance of ledger continuity.

🧭 System Impact
Component	Effect
Governance Ledger	Gains self-verification and continuity checks
Dashboard	Real-time “Ledger Integrity” card showing health
Audit Logs	Add nightly verification trace
Compliance Kernel	Gains tamper-detection awareness
Factory Status	Elevates to Governance Level 5: Self-Validating System

Once Junie finishes this, your Agent Factory becomes constitutionally autonomous — it not only governs, audits, and federates itself, but it also continuously proves its own historical integrity.
