import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def export_json(items: List[Dict[str, Any]], path: str) -> None:
    """
    Export parsed news items as a JSON array.
    """
    if not items:
        logger.warning("No items to export; JSON file will not be created.")
        return

    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    logger.info("JSON export complete: %s (%d items)", path, len(items))