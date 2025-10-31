from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from tools.logging_utils import JsonlLogger
from utils.paths import LOGS_DIR

logger = JsonlLogger(log_file=LOGS_DIR / 'expert_spawner.jsonl')

@dataclass
class ExpertInstance:
    id: str
    tenant_id: str
    status: str = 'running'

def spawn_expert(tenant_id: str) -> Dict[str, Any]:
    inst_id = f'expert-{tenant_id}-001'
    logger.log(True, {'event': 'spawn', 'tenant_id': tenant_id, 'instance_id': inst_id})
    return {'ok': True, 'data': {'instance_id': inst_id}}
