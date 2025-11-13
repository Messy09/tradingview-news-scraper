import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def clean_whitespace(text: Optional[str]) -> str:
    """Normalize whitespace and handle None values."""
    if text is None:
        return ""
    return " ".join(str(text).split())

def parse_unix_timestamp(value: Any) -> Optional[int]:
    """
    Ensure we always return a UNIX timestamp (seconds since epoch) or None.

    Accepts:
    - int / float
    - numeric string
    - ISO 8601 date string (e.g., '2023-06-05T12:00:00Z')
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    # Numeric string
    if text.isdigit():
        return int(text)

    # ISO-ish format
    try:
        # Handle trailing Z
        if text.endswith("Z"):
            text = text[:-1]
            dt = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        logger.debug("Could not parse timestamp from value %r", value)
        return None

def normalize_related_symbols(raw: Any) -> List[Dict[str, Any]]:
    """
    Ensure relatedSymbols is always a list of dictionaries with at least a 'symbol' key.
    """
    if raw is None:
        return []

    if isinstance(raw, dict):
        return [raw]

    if not isinstance(raw, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            symbol = str(item.get("symbol", "")).strip()
            if not symbol:
                continue
            normalized.append(
                {
                    "symbol": symbol,
                    "logoid": item.get("logoid") or item.get("logoId") or "",
                    "logourl": item.get("logourl") or item.get("logoUrl") or "",
                }
            )
        elif isinstance(item, str):
            symbol = item.strip()
            if symbol:
                normalized.append({"symbol": symbol, "logoid": "", "logourl": ""})

    return normalized

def shorten_text(text: str, max_length: int = 220) -> str:
    """
    Shorten a piece of text to a maximum length, cutting cleanly at word boundaries.
    """
    text = clean_whitespace(text)
    if len(text) <= max_length:
        return text

    truncated = text[: max_length - 1]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"