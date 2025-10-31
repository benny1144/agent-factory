from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class FederationInterface:
    """Simple interface for Orion to communicate with Watchtower chat feed.

    Appends entries to logs/chat/watchtower_room.jsonl.
    """

    def __init__(self, repo_root: pathlib.Path) -> None:
        self.repo_root = pathlib.Path(repo_root)
        self.chat_log = self.repo_root / "logs" / "chat" / "watchtower_room.jsonl"
        self.chat_log.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, entry: Dict[str, Any]) -> None:
        try:
            with self.chat_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def announce_online(self) -> None:
        entry = {"agent": "Orion", "event": "online", "message": "Orion Control Plane activated."}
        self._append(entry)

    def relay_message(self, sender: str, message: str) -> None:
        entry = {"agent": sender, "event": "message", "content": message}
        self._append(entry)
