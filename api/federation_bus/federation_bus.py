from __future__ import annotations
from typing import Dict, Any, Callable
from tools.logging_utils import JsonlLogger
from utils.paths import LOGS_DIR

class FederationBus:
    def __init__(self) -> None:
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.logger = JsonlLogger(log_file=LOGS_DIR / 'federation_bus.jsonl')
    def register(self, topic: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.handlers[topic] = handler
    def send(self, topic: str, msg: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log(True, {'event': 'send', 'topic': topic, 'msg': msg})
        h = self.handlers.get(topic)
        if not h:
            return {'ok': False, 'error': 'no_handler'}
        resp = h(msg)
        self.logger.log(True, {'event': 'recv', 'topic': topic, 'resp': resp})
        return resp
