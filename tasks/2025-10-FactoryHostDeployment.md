[JUNIE TASK]

Title: Implement Factory-Hosted Deployment & Client Namespace System

Preconditions:

Repo: benny1144/agent-factory

Branch: deployment/factory_hosted_clients

Genesis, Archy, and Junie active

Governance Console operational (FastAPI + React UI)

Compliance kernel functional

🧩 Phase 1 — Client Namespace Architecture

Plan:

Create directory schema under project root:

/clients/
/<client_name>/
/agents/
/data/
/logs/
/governance/


Each client namespace mirrors the Factory structure but with sandboxed access and audit boundaries.

Add configuration template: /config/client_registry.yaml

clients:
acme_corp:
id: CL-001
contact: admin@acme.com
namespace_path: clients/acme_corp/
active: true
governance_level: external_sandbox
nova_ai:
id: CL-002
contact: lead@nova.ai
namespace_path: clients/nova_ai/
active: false
governance_level: inactive


Add helper module: /src/factory/namespace_manager.py

import yaml, os, shutil, datetime

def load_registry():
with open("config/client_registry.yaml") as f:
return yaml.safe_load(f)

def create_namespace(client_name):
base = f"clients/{client_name}"
os.makedirs(f"{base}/agents", exist_ok=True)
os.makedirs(f"{base}/data", exist_ok=True)
os.makedirs(f"{base}/logs", exist_ok=True)
os.makedirs(f"{base}/governance", exist_ok=True)
with open(f"{base}/governance/README.md", "w") as f:
f.write(f"Governance space for {client_name}\nCreated {datetime.datetime.utcnow()}\n")
print(f"[Namespace] Created: {base}")

def archive_namespace(client_name):
shutil.make_archive(f"dist/{client_name}_namespace", "zip", f"clients/{client_name}")
print(f"[Namespace] Archived {client_name} → dist/{client_name}_namespace.zip")

🧩 Phase 2 — Agent Packaging Tool

Create tool: /tools/factory_packager.py

import os, tarfile, argparse, datetime, yaml

def package_agent(agent_name, output_dir="dist", client=None):
base = f"agents/{agent_name}"
ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
filename = f"{output_dir}/{agent_name}_{ts}.tar.gz"
os.makedirs(output_dir, exist_ok=True)

    with tarfile.open(filename, "w:gz") as tar:
        for item in ["persona_archivist.yaml", "main.py", "requirements.txt"]:
            path = os.path.join(base, item)
            if os.path.exists(path):
                tar.add(path, arcname=os.path.join(agent_name, item))
    meta = {
        "agent": agent_name,
        "client": client,
        "timestamp": ts,
        "origin_factory": "AgentFactory-Core",
    }
    with open(f"{output_dir}/{agent_name}_metadata.yaml", "w") as f:
        yaml.dump(meta, f)
    print(f"[Packager] Created package: {filename}")

if __name__ == "__main__":
parser = argparse.ArgumentParser(description="Factory Agent Packager")
parser.add_argument("--agent", required=True, help="Agent name to package")
parser.add_argument("--client", help="Optional client name")
parser.add_argument("--output", default="dist", help="Output directory")
args = parser.parse_args()
package_agent(args.agent, args.output, args.client)


Usage examples:

python tools/factory_packager.py --agent archivist
python tools/factory_packager.py --agent financial_crew --client acme_corp

🧩 Phase 3 — Governance Integration

Extend /governance/agents_registry.yaml:

agents:
- name: archivist
  id: AF-001
  namespace: global
  status: active
- name: financial_crew
  id: CL-001-FA
  namespace: acme_corp
  status: packaged


Create new audit log: /compliance/audit_log/client_deployments.csv

timestamp, client, agent, version, action, outcome, trace_id


When packaging or creating namespaces, automatically append entries here for traceability.

🧩 Phase 4 — Dashboard UI Integration

Backend:
Add API route /clients/registry → returns parsed client_registry.yaml.

Frontend:
Add “Clients” tab with cards for each registered namespace:

Name

Governance level

Active/Inactive status

Last deployment timestamp

Each card can show available agents (/clients/<client>/agents/) and options:

Download package

Deploy/Reactivate

Archive namespace

🧩 Phase 5 — Verification

Tests:

python -m src.factory.namespace_manager create_namespace acme_corp
python tools/factory_packager.py --agent archivist --client acme_corp


Verify:

Directories created under /clients/acme_corp/

Tarball output under /dist/

Audit log entries appended

Dashboard lists new client with deployment data

Governance validation:
Run validate_kba_registry.py — ensure new namespaces registered and valid.

🧾 Rollback

Delete /clients/ directory and /dist/ artifacts.

Revert factory_packager.py, namespace_manager.py, and YAML registry changes.

Reactivate Genesis and governance console.

✅ Expected Results

You can create isolated client workspaces within Factory.

Agents can be packaged, versioned, and exported with one command.

Governance records every package and deployment.

Dashboard displays client and deployment information.

All activity is logged and auditable.

Phase 6 — Federation Enablement

Purpose:
Allow client-deployed or Factory-hosted agents to participate in knowledge sharing without compromising governance, provenance, or ethical baselines.

Plan

Extend the KBA Registry

Update /config/kba_registry.yaml to include federated nodes:

kba_nodes:
- id: factory_core
  uri: https://factory.agent.local/api/kba
  type: core
  trust_level: root
- id: acme_corp_node
  uri: https://acme.agentfactory.ai/api/kba
  type: client
  trust_level: federated
  sync_policy: pull_approved_only
- id: nova_ai_node
  uri: https://nova.agentfactory.ai/api/kba
  type: client
  trust_level: federated
  sync_policy: bidirectional


Create a Federation Service

New module: /src/factory/federation_manager.py

import requests, yaml, time, logging

def load_nodes():
with open("config/kba_registry.yaml") as f:
return yaml.safe_load(f)["kba_nodes"]

def sync_to_core(node):
try:
r = requests.get(f"{node['uri']}/export", timeout=10)
if r.status_code == 200:
data = r.json()
requests.post("https://factory.agent.local/api/kba/import", json=data, timeout=10)
logging.info(f"[Federation] Synced {node['id']} → core")
except Exception as e:
logging.error(f"[Federation] Sync error from {node['id']}: {e}")

def run_federation_loop(interval=3600):
while True:
for node in load_nodes():
if node["trust_level"] == "federated":
sync_to_core(node)
time.sleep(interval)


Governance Control

Add /governance/policies/federation_policy.yaml:

approval_required: true
ethics_check: true
provenance_hash_required: true
max_sync_interval_hours: 1


Genesis validates any imported knowledge against this policy before merging into the core KBA.

Audit & Ledger

New audit log: /compliance/audit_log/federation_syncs.csv

timestamp, source_node, target_node, records_imported, status, reviewer


Automatically updated by the federation_manager after every sync attempt.

Dashboard Integration

Backend endpoint /federation/status returning last 50 sync events.

Frontend “Federation Monitor” card showing:

Active nodes

Last sync timestamp

Records synced

Pending approvals

Testing / Verification

python -m src.factory.federation_manager run_federation_loop


Simulate a remote node by exposing /api/kba/export on a client namespace.

Verify imported knowledge appears in the core Factory KBA viewer.

Check audit log entries and Governance Dashboard updates.

Rollback

Stop federation loop process.

Remove federation nodes from kba_registry.yaml.

Delete /src/factory/federation_manager.py and associated policy file.

✅ Expected Outcome

Every client namespace can run its own “mini-factory node.”

Knowledge contributed by client agents syncs back under signed, auditable, and ethics-checked conditions.

The Governance Dashboard gains a “Federation Monitor” that tracks node status and synchronization integrity.

Genesis and Archy can now both reference federated knowledge during future builds or briefings.

Once Junie completes this addition, your Agent Factory will have a full lifecycle:

You → Archy → Genesis → Junie → Governance → Federation

…making it a living, distributed, ethically governed intelligence ecosystem.

Phase 7 — Federation Security Checklist

Purpose:
To enforce integrity, provenance, and ethical compliance across all federated nodes during KBA synchronization.
Ensures that no external knowledge enters the Factory Core without digital signature validation, ethical conformity checks, and provenance proof.

🔒 Security Validation Workflow

Signature Verification

Every federated node (client mini-factory) must register its public key in:
/governance/federation_keys.yaml

federation_keys:
acme_corp_node:
public_key: |
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqh...
-----END PUBLIC KEY-----
nova_ai_node:
public_key: |
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqh...
-----END PUBLIC KEY-----


During each sync, the federation_manager.py validates the signed payload header:

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

def verify_signature(node_id, data, signature):
key = load_key_for_node(node_id)
key.verify(
signature,
data.encode(),
padding.PKCS1v15(),
hashes.SHA256()
)
return True


Provenance Hash Validation

Each exported knowledge batch includes a provenance hash:

{
"batch_id": "UUID",
"records": [...],
"provenance_hash": "sha256:abc123..."
}


Genesis recomputes this hash upon receipt and logs:

[Federation] Verified provenance hash for acme_corp_node batch UUID


Mismatched hashes → quarantined until reviewed.

Ethical Baseline Compliance

Each node maintains a local ethical baseline (ethical_baseline_v2.json).

On sync, Genesis compares the node’s baseline delta against the Factory’s current version.

If drift exceeds ETHICAL_DRIFT_THRESHOLD (default 0.05), the sync is delayed and flagged in:
/compliance/audit_log/ethical_drift_alerts.csv.

Human Firewall (HITL) Review

If any of the above checks fail:

Genesis triggers a “Review Required” event to the Governance Console.

HITL reviewer must manually approve or reject the batch.

Decision outcome appended to /compliance/audit_log/federation_syncs.csv.

Continuous Monitoring

Health and integrity checks added to federation_manager:

Every 6 hours, verify each node’s signature validity (using cached challenge).

Report any inactive or compromised node in Governance Dashboard > Federation Monitor.

🧾 Audit and Compliance Outputs
File	Description
/compliance/audit_log/federation_syncs.csv	Logs each synchronization with source, target, size, and status.
/compliance/audit_log/federation_verifications.csv	Records every signature + hash validation event.
/compliance/audit_log/ethical_drift_alerts.csv	Flags nodes that show baseline drift above the allowed threshold.
/governance/federation_keys.yaml	Stores all registered node public keys.
✅ Verification Checklist
Check	Description	Validation Command
✅ Key registration	Each federated node has a valid public key	python -m src.factory.federation_manager verify-keys
✅ Signature validation	All sync payloads verified successfully	Inspect federation_verifications.csv
✅ Provenance hash	All imported batches match local hash	CI pipeline step validate_provenance.py
✅ Ethical compliance	Drift ≤ threshold	python -m governance.ethics.validate_drift
✅ HITL review	Manual review completed if triggered	Governance Console > Federation Monitor
✅ Audit consistency	No missing log entries	python -m compliance.validate_audit_trail
⚙️ Rollback

If a node is found compromised:

Deactivate its federation entry in /config/kba_registry.yaml (active: false).

Revoke its public key in /governance/federation_keys.yaml.

Purge any unverified imported batches from /kba/federated_inbox/.

Run python -m governance.ethics.restore_baseline to re-sync ethical state.

🌐 Expected Outcome

Every federated client’s knowledge sync is digitally signed, provenance-verified, and ethically validated.

Any deviation triggers governance alerts, requiring human review.

The Governance Dashboard reflects real-time sync and verification status.

Federation is now secure, traceable, and fully compliant with your Human Firewall Protocol.

