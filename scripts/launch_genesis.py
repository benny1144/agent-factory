import subprocess, sys

# Run governance startup check first
rc = subprocess.call([sys.executable, "scripts/startup_check.py"])
if rc != 0:
    sys.exit(rc)

# If healthy, run the Genesis Architect crew
sys.exit(subprocess.call([sys.executable, "agents/architect_genesis/main.py"]))
