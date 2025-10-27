"""
Payload Validator for Genesis Build Requests
--------------------------------------------
Validates agent creation payloads before submission to Genesis.
Checks schema integrity, path existence, and governance compliance.
Supports both JSON and YAML payload formats.
"""

from __future__ import annotations
import json
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List

# === CONFIGURATION ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOADS_DIR = PROJECT_ROOT / "payloads"
GOV_FILE = PROJECT_ROOT / "factory_governance/genesis_principles.yaml"

# === BASIC SCHEMA EXPECTATIONS ===
REQUIRED_FIELDS = [
    "agent_name",
    "codename",
    "purpose",
    "capabilities",
    "constraints",
    "implementation_targets",
    "dependencies",
    "coordination",
    "verification",
]

# === UTILITY FUNCTIONS ===
def load_payload(path: Path) -> Dict[str, Any]:
    """Load and parse JSON or YAML payload file."""
    if not path.exists():
        sys.exit(f"[ERROR] File not found: {path}")

    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            sys.exit(f"[ERROR] File is empty: {path}")

        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(text)
        return json.loads(text)

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        sys.exit(f"[ERROR] Invalid format in {path.name}: {e}")

def validate_required_fields(data: Dict[str, Any]):
    """Ensure all mandatory schema fields are present."""
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        sys.exit(f"[ERROR] Missing required fields: {missing}")
    print(f"[OK] All required fields present ({len(REQUIRED_FIELDS)}).")

def validate_target_paths(targets: List[str]):
    """Verify all implementation target paths reference valid structure."""
    invalid = []
    for target in targets:
        full_path = PROJECT_ROOT / target
        if not full_path.parent.exists():
            invalid.append(str(full_path.parent))
    if invalid:
        sys.exit("[ERROR] Invalid or missing target directories:\n  - " + "\n  - ".join(invalid))
    print(f"[OK] Verified {len(targets)} implementation targets.")

def validate_governance_doctrine():
    """Ensure the Genesis doctrine file exists and is readable."""
    if not GOV_FILE.exists():
        sys.exit(f"[ERROR] Missing governance doctrine file: {GOV_FILE}")
    try:
        _ = yaml.safe_load(GOV_FILE.read_text(encoding="utf-8"))
        print(f"[OK] Governance doctrine validated: {GOV_FILE.name}")
    except yaml.YAMLError as e:
        sys.exit(f"[ERROR] Invalid YAML in governance doctrine: {e}")

def validate_integrations(data: Dict[str, Any]):
    """Optional: Validate external research or API integration metadata."""
    integration = data.get("integration", {})
    if not integration:
        print("[WARN] No 'integration' section found in payload.")
        return

    if "doctrine_file" not in integration:
        print("[WARN] Missing 'doctrine_file' reference in integration section.")

    if "research_integrations" in integration:
        integrations = integration["research_integrations"]
        if isinstance(integrations, list):
            print(f"[OK] Research integrations detected: {', '.join(integrations)}")
        else:
            print("[WARN] 'research_integrations' should be a list.")

# === MAIN ===
def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python tools/payload_validator.py <path_to_payload.json|yaml>")

    payload_path = Path(sys.argv[1])
    print(f"\n[Genesis Validator] Validating payload: {payload_path.name}\n")

    data = load_payload(payload_path)
    validate_required_fields(data)
    validate_target_paths(data.get("implementation_targets", []))
    validate_governance_doctrine()
    validate_integrations(data)

    print("\n✅ Payload validation successful.")
    print(f"→ Ready for Genesis build submission: {payload_path.name}\n")

if __name__ == "__main__":
    main()
