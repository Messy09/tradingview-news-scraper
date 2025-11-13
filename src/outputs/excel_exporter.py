import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - environment dependent
    pd = None

def export_excel(items: List[Dict[str, Any]], path: str) -> None:
    """
    Export parsed news items to an Excel (.xlsx) file using pandas.
    """
    if not items:
        logger.warning("No items to export; Excel file will not be created.")
        return

    if pd is None:
        logger.error(
            "pandas is required for Excel export but is not installed. "
            "Install 'pandas' and 'openpyxl' to enable this feature."
        )
        return

    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    df = pd.DataFrame(items)
    df.to_excel(path, index=False)
    logger.info("Excel export complete: %s (%d items)", path, len(items))