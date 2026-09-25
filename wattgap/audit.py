"""Append-only JSONL audit log: one line per decision, approval, alarm or quarantine."""

from __future__ import annotations

import json
from pathlib import Path


class AuditLog:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[dict] = []
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, ts: float, actor: str, kind: str, **fields) -> dict:
        event = {"seq": len(self.events) + 1, "ts": round(ts, 3), "actor": actor, "kind": kind, **fields}
        self.events.append(event)
        if self.path:
            with self.path.open("a") as f:
                f.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def of_kind(self, *kinds: str) -> list[dict]:
        return [e for e in self.events if e["kind"] in kinds]
