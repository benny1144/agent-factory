import os, subprocess, datetime, sys

def log(msg):
    os.makedirs("logs", exist_ok=True)
    with open("logs/compliance_startup.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

print("🔍 Verifying Junie Bridge health...")
result = subprocess.run([sys.executable, "scripts/verify_bridge_health.py"], capture_output=True, text=True)
log(result.stdout.strip())

if result.returncode == 0:
    print("✅ Bridge healthy — continuing startup.")
else:
    print("❌ Bridge unhealthy — startup aborted.")
    log("Startup blocked: Bridge verification failed.")
    sys.exit(result.returncode)
