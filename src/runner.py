import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Ensure src/ is on the Python path so we can import internal modules
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from extractors.tradingview_parser import TradingViewNewsParser  # type: ignore
from outputs.json_exporter import export_json  # type: ignore
from outputs.csv_exporter import export_csv  # type: ignore
from outputs.excel_exporter import export_excel  # type: ignore

def load_settings() -> Dict[str, Any]:
    """Load settings from config/settings.json or fallback to settings.example.json."""
    config_dir = os.path.join(BASE_DIR, "config")
    primary = os.path.join(config_dir, "settings.json")
    fallback = os.path.join(config_dir, "settings.example.json")

    path = primary if os.path.exists(primary) else fallback
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Failed to load settings from {path}: {exc}")
        return {}

def resolve_path(path: str, project_root: str) -> str:
    """Resolve a possibly relative path against the project root."""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.join(project_root, path)

def load_input(path: str) -> List[Dict[str, Any]]:
    """Load TradingView news JSON input."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        # Support dict with "items" or similar top-level key
        items = data.get("items") or data.get("results")
        if isinstance(items, list):
            return items
        return [data]

    if not isinstance(data, list):
        raise ValueError("Input JSON must be an object or array of objects")

    return data

def configure_logging(level_name: str) -> None:
    """Configure root logger."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def run_pipeline(
    input_items: List[Dict[str, Any]],
    output_format: str,
    output_path: str,
    provider_filter: str | None,
    symbols_filter: List[str] | None,
    min_urgency: int | None,
) -> None:
    """Parse raw TradingView items and export in the requested format."""
    logger = logging.getLogger("runner")

    symbol_filter_set = set(symbols_filter) if symbols_filter else None
    parser = TradingViewNewsParser(
        symbol_filter=symbol_filter_set,
        provider_filter=provider_filter,
        min_urgency=min_urgency,
    )

    logger.info("Parsing %d raw items", len(input_items))
    parsed_items = parser.parse(input_items)
    logger.info("Parsed %d items after filtering", len(parsed_items))

    if not parsed_items:
        logger.warning("No items produced after parsing and filtering; nothing to export.")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if output_format == "json":
        export_json(parsed_items, output_path)
    elif output_format == "csv":
        export_csv(parsed_items, output_path)
    elif output_format == "excel":
        export_excel(parsed_items, output_path)
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported output format: {output_format}")

    logger.info("Export complete -> %s", output_path)

def build_arg_parser(settings: Dict[str, Any]) -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="TradingView News Scraper - process and export TradingView news data."
    )

    default_input = settings.get("input_file") or os.path.join("data", "sample_input.json")
    default_format = settings.get("output_format", "json")
    default_output_dir = settings.get("output_dir") or "data"
    default_output_path = settings.get("output_path") or ""

    parser.add_argument(
        "--input",
        dest="input_path",
        default=default_input,
        help=f"Path to input JSON file (default: {default_input})",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "csv", "excel"],
        default=default_format,
        help=f"Output format (default: {default_format})",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=default_output_path,
        help="Output file path. If omitted, a file in the configured output_dir is used.",
    )
    parser.add_argument(
        "--provider",
        dest="provider_filter",
        default=settings.get("provider_filter"),
        help="Filter results by provider name (case-insensitive).",
    )
    parser.add_argument(
        "--symbol",
        dest="symbols",
        action="append",
        help="Filter results by related symbol (e.g. NASDAQ:GOOG). Can be used multiple times.",
    )
    parser.add_argument(
        "--min-urgency",
        dest="min_urgency",
        type=int,
        default=settings.get("min_urgency"),
        help="Minimum urgency value to include (integer).",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=settings.get("log_level", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the first parsed item instead of exporting (for quick inspection).",
    )

    parser.set_defaults(
        default_output_dir=default_output_dir,
    )

    return parser

def main() -> None:
    settings = load_settings()
    parser = build_arg_parser(settings)
    args = parser.parse_args()

    configure_logging(args.log_level)
    logger = logging.getLogger("runner")

    input_path = resolve_path(args.input_path, PROJECT_ROOT)
    logger.info("Using input file: %s", input_path)

    try:
        raw_items = load_input(input_path)
    except Exception as exc:
        logger.error("Failed to load input: %s", exc, exc_info=True)
        sys.exit(1)

    output_format = args.output_format
    default_output_dir = resolve_path(args.default_output_dir, PROJECT_ROOT)

    if args.output_path:
        output_path = resolve_path(args.output_path, PROJECT_ROOT)
    else:
        ext = {"json": "json", "csv": "csv", "excel": "xlsx"}[output_format]
        file_name = f"tradingview_news.{ext}"
        output_path = os.path.join(default_output_dir, file_name)

    if args.preview:
        parser_obj = TradingViewNewsParser(
            symbol_filter=set(args.symbols) if args.symbols else None,
            provider_filter=args.provider_filter,
            min_urgency=args.min_urgency,
        )
        parsed = parser_obj.parse(raw_items)
        if parsed:
            print(json.dumps(parsed[0], ensure_ascii=False, indent=2))
        else:
            logger.warning("No items found after parsing.")
        return

    run_pipeline(
        input_items=raw_items,
        output_format=output_format,
        output_path=output_path,
        provider_filter=args.provider_filter,
        symbols_filter=args.symbols,
        min_urgency=args.min_urgency,
    )

if __name__ == "__main__":
    main()