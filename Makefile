# Agent Factory Makefile

.PHONY: start genesis validate validate-fix

start:
	@python scripts/startup_check.py && python agents/architect_genesis/main.py

# Backward-compatible alias
genesis: start

validate:
	python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs

validate-fix:
	python scripts/validate_kba_registry.py --root . --registry registry/metadata_index.json --audit-dir validation/logs --fix
