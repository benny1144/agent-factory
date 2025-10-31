# Payloads

Purpose: Store machine-readable payloads sent to Genesis or other system orchestrators.

This directory contains JSON payloads that describe build or orchestration requests. For example, commissioning a new agent via Genesis.

## Archivist Creation Payload Schema

A minimal expected schema for `archivist_creation_request.json`:

- agent_name: string (required) — Human-readable name of the agent
- codename: string (required) — Short codename used across logs and UI
- purpose: string (required) — One-line description of the agent’s mission
- capabilities: array[string] (required) — List of capabilities
- constraints: object (required)
  - code_execution: boolean
  - system_modifications: boolean
  - file_writes_logged: boolean
  - governance_hooks_required: boolean
- implementation_targets: array[string] (required) — Paths Genesis/Junie should produce or modify
- dependencies: array[string] (required) — Runtime/library deps the agent may require
- coordination: object (required)
  - genesis: string — Responsibility of Genesis
  - junie: string — Responsibility of Junie
- verification: object (required)
  - junie_validation_pass: boolean
  - governance_registry_entry: boolean
  - health_check_endpoint: string

## Usage

1) Validate the payload

   make payload-validate

   or

   python scripts/send_archivist_build.py --validate payloads/archivist_creation_request.json

2) Send the build request to Genesis (requires Genesis listener running on localhost:5055)

   make payload-send

   or

   python scripts/send_archivist_build.py --send payloads/archivist_creation_request.json

Artifacts will be written under `artifacts/payloads/` including any JSON response from Genesis for audit and traceability.
