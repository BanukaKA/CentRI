from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from centri.config import Settings


class ShadowLogger:
    def __init__(self, settings: Settings) -> None:
        self.dir = settings.centri_shadow_log_dir
        self.retention_days = settings.centri_log_retention_days
        self.redact = settings.centri_redact_telemetry
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cleanup()

    def log(self, event: dict[str, Any]) -> Path:
        event = self._safe_event(event)
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.dir / f"shadow_{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return path

    def _safe_event(self, event: dict[str, Any]) -> dict[str, Any]:
        safe = dict(event)
        if self.redact:
            for field in ("prompt", "query", "history"):
                if field in safe:
                    value = json.dumps(safe.pop(field), sort_keys=True)
                    safe[f"{field}_sha256"] = hashlib.sha256(value.encode("utf-8")).hexdigest()
                    safe[f"{field}_length"] = len(value)
        return safe

    def cleanup(self) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - (self.retention_days * 86400)
        for path in self.dir.glob("shadow_*.jsonl"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
