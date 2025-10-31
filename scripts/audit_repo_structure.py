import os, json, pathlib

# Always start at repo root (one level above this script)
repo_root = pathlib.Path(__file__).resolve().parents[1]

expected = ["main.py", "requirements.txt"]
report = {}

# Walk through all agent directories
for root, dirs, files in os.walk(repo_root / "factory_agents"):
    if "__pycache__" in root:
        continue

    rel = pathlib.Path(root).relative_to(repo_root)
    parts = rel.parts

    # Only consider folders directly under factory_agents
    if len(parts) > 1 and parts[0] == "factory_agents":
        agent_name = parts[1]
        # Check expected files inside this directory
        missing = [f for f in expected if f not in files]
        report[agent_name] = {
            "missing": missing,
            "status": "ok" if not missing else "incomplete"
        }

# Ensure audit folder exists
audit_dir = repo_root / "governance" / "audits"
audit_dir.mkdir(parents=True, exist_ok=True)

# Write results
output_file = audit_dir / "repo_structure.json"
output_file.write_text(json.dumps(report, indent=2))

print(f"✅ Repo structure audit written to: {output_file.resolve()}")
print("Agents scanned:", len(report))
