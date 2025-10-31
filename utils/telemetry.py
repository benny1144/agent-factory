from __future__ import annotations
from tools.logging_utils import JsonlLogger
from utils.paths import LOGS_DIR

_log = JsonlLogger(log_file=LOGS_DIR / 'infra_health.jsonl')

def record_health(service: str, ok: bool, **fields) -> None:
    data = {'event': 'service_health', 'service': service, 'ok': ok, **fields}
    _log.log(ok, data)
