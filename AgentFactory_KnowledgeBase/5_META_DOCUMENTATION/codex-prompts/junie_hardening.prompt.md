You are Codex assisting with reliability hardening.
Goal: make the executor idempotent, sandboxed, fully logged.
Constraints: no external side effects, add try/except, structured errors.
Add wrappers that log start/end, args, result to audit logger.
Generate unit tests for failure paths, timeouts, and retries (expo backoff).
