from __future__ import annotations

import base64
import csv
import io
import json
from typing import Literal

from mcp_core.models.datasets import SeriesTable


def export_table(
    dataset_id: str,
    table: SeriesTable,
    fmt: Literal["csv", "json"],
) -> tuple[str, str, str]:
    """Export a SeriesTable to CSV or JSON.

    Returns (content_base64, filename, mime_type).
    """

    if fmt == "json":
        payload = {
            "columns": [c.model_dump() for c in table.columns],
            "rows": table.rows,
            "metadata": table.metadata,
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        filename = f"{dataset_id}.json"
        mime_type = "application/json"
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([c.name for c in table.columns])
        for row in table.rows:
            writer.writerow(row)
        raw = buf.getvalue().encode("utf-8")
        filename = f"{dataset_id}.csv"
        mime_type = "text/csv"
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    content_b64 = base64.b64encode(raw).decode("ascii")
    return content_b64, filename, mime_type
