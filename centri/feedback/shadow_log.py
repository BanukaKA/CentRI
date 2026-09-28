from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from centri.config import Settings


class ShadowLogger:
    def __init__(self, settings: Settings) -> None:
        self.dir = settings.centri_shadow_log_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict[str, Any]) -> Path:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.dir / f"shadow_{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return path
