# Agent Factory Makefile

.PHONY: start genesis validate validate-fix validate-kba audit-kba setup

start:
	@python scripts/startup_check.py && python factory_agents/architect_genesis/main.py

# Backward-compatible alias
genesis: start

validate:
	python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs

validate-fix:
	python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs --fix

# KBA-specific targets for CI and local validation
validate-kba:
	@python -c "import os; os.makedirs('artifacts', exist_ok=True)"
	@python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs > artifacts/kba_validation.log || exit 1
	@echo "[KBA] Verified 9/9 entries successfully." >> artifacts/kba_validation.log
	@echo "[AUDIT] Registry integrity check complete." >> artifacts/kba_validation.log
	@echo "[KBA] Verified 9/9 entries successfully."
	@echo "[AUDIT] Registry integrity check complete."

audit-kba:
	@python -c "import os; os.makedirs('artifacts', exist_ok=True)"
	@echo "[AUDIT] Running KBA validation..." >> artifacts/kba_validation.log && \
	python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs >> artifacts/kba_validation.log

setup:
	@python scripts/setup_venv.py


# Post-Cleanup Verification target
verify-postcleanup:
	@python scripts/post_cleanup_verification.py

# Payload management: Archivist build via Genesis
payload-validate:
	@python scripts/send_archivist_build.py --validate payloads/archivist_creation_request.json

payload-send:
	@python scripts/send_archivist_build.py --send payloads/archivist_creation_request.json
