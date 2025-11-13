import csv
import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def _ensure_serializable(value: Any) -> str:
    """
    Convert arbitrary Python values into CSV-compatible strings.
    Lists and dicts are JSON-encoded; everything else is cast to str.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)

def export_csv(items: List[Dict[str, Any]], path: str) -> None:
    """
    Export parsed news items to CSV.
    """
    if not items:
        logger.warning("No items to export; CSV file will not be created.")
        return

    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # Determine header fields from union of all item keys
    fieldnames = sorted({key for item in items for key in item.keys()})

    with open(path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = {key: _ensure_serializable(item.get(key)) for key in fieldnames}
            writer.writerow(row)

    logger.info("CSV export complete: %s (%d items)", path, len(items))