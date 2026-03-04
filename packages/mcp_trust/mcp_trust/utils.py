from __future__ import annotations

import json
from typing import Any


def json_dump_safe(value: Any) -> str:
    """Serialize a value to JSON for heuristics without raising."""

    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)

