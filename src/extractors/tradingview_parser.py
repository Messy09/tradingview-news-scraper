import logging
from typing import Any, Dict, Iterable, List, Optional, Set

from extractors.content_utils import (
    clean_whitespace,
    normalize_related_symbols,
    parse_unix_timestamp,
    shorten_text,
)

logger = logging.getLogger(__name__)

class TradingViewNewsParser:
    """
    Parser and normalizer for TradingView news items.

    This class takes raw JSON-like dictionaries (e.g. direct TradingView API
    responses or pre-saved JSON) and produces a clean, consistent structure
    that can be exported to various formats.
    """

    def __init__(
        self,
        symbol_filter: Optional[Set[str]] = None,
        provider_filter: Optional[str] = None,
        min_urgency: Optional[int] = None,
    ) -> None:
        self.symbol_filter = {s.upper() for s in symbol_filter} if symbol_filter else None
        self.provider_filter = provider_filter.lower() if provider_filter else None
        self.min_urgency = min_urgency

    def _matches_filters(self, item: Dict[str, Any]) -> bool:
        """Return True if the parsed item passes configured filters."""
        if self.provider_filter:
            provider = str(item.get("provider", "")).lower()
            if provider != self.provider_filter:
                return False

        if self.min_urgency is not None:
            urgency = item.get("urgency")
            try:
                if urgency is None or int(urgency) < int(self.min_urgency):
                    return False
            except (TypeError, ValueError):
                return False

        if self.symbol_filter:
            symbols = {
                str(sym.get("symbol", "")).upper()
                for sym in item.get("relatedSymbols") or []
                if isinstance(sym, dict)
            }
            if not symbols.intersection(self.symbol_filter):
                return False

        return True

    @staticmethod
    def _extract_text(raw: Dict[str, Any]) -> str:
        """
        Determine the best full description text from available fields.
        Prefers `descriptionText`, falls back to AST description or short description.
        """
        text = raw.get("descriptionText") or raw.get("astDescription") or raw.get("shortDescription") or ""
        return clean_whitespace(text)

    def parse_item(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single TradingView news item into a consistent schema.
        """
        item_id = str(raw.get("id") or "").strip()
        title = clean_whitespace(raw.get("title"))
        provider = clean_whitespace(raw.get("provider"))
        source_logo_url = raw.get("sourceLogoUrl") or raw.get("logoUrl") or ""
        source_logo_url = clean_whitespace(source_logo_url)
        published_ts = parse_unix_timestamp(raw.get("published"))
        source = clean_whitespace(raw.get("source"))
        urgency = raw.get("urgency")
        permission = clean_whitespace(raw.get("permission"))

        story_path = raw.get("storyPath") or raw.get("url") or ""
        story_path = clean_whitespace(story_path)

        full_text = self._extract_text(raw)
        short_description = clean_whitespace(raw.get("shortDescription"))
        if not short_description and full_text:
            short_description = shorten_text(full_text, max_length=200)

        related_symbols = normalize_related_symbols(raw.get("relatedSymbols"))

        normalized: Dict[str, Any] = {
            "id": item_id,
            "title": title,
            "provider": provider,
            "sourceLogoUrl": source_logo_url,
            "published": published_ts,
            "source": source,
            "urgency": urgency,
            "permission": permission,
            "relatedSymbols": related_symbols,
            "storyPath": story_path,
            "astDescription": clean_whitespace(raw.get("astDescription")),
            "descriptionText": full_text,
            "shortDescription": short_description,
        }

        return normalized

    def parse(self, raw_items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse a collection of raw items, returning normalized items that pass filters.
        """
        parsed: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                logger.warning("Skipping non-dict item at index %d: %r", idx, raw)
                continue
            try:
                item = self.parse_item(raw)
            except Exception as exc:
                logger.error("Failed to parse item at index %d: %s", idx, exc, exc_info=True)
                continue

            if self._matches_filters(item):
                parsed.append(item)

        return parsed