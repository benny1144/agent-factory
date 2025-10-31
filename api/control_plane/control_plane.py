from __future__ import annotations
from typing import Dict, Any
from api.federation_bus.federation_bus import FederationBus

class ControlPlane:
    def __init__(self, bus: FederationBus) -> None:
        self.bus = bus
        self.bus.register('control.echo', self._echo)
    def _echo(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        return {'ok': True, 'echo': msg}
