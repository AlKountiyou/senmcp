from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonlAuditLogger:
    """Append-only JSONL logger for trust & safety events."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            **record,
        }
        line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)

        # Best-effort atomic append; on POSIX, append writes are atomic for small records.
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        fd = os.open(self._path, flags, 0o600)
        try:
            os.write(fd, (line + "\n").encode("utf-8"))
        finally:
            os.close(fd)
