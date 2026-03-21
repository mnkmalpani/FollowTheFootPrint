"""CLI entry point – ``uv run ftf`` or ``python -m followthefootprints``."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from .analyzer import INTERVAL_MODE_MAP, FollowTheFootPrints

# Load .env so TELEGRAM_* are available when run on server
load_dotenv()
from .indices import INDEX_LISTS

_MODE_TO_INTERVAL = {v: k for k, v in INTERVAL_MODE_MAP.items()}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ftf",
        description="Follow The Footprints – demand zone scanner",
    )
    parser.add_argument(
        "--mode",
        choices=["weekly", "daily"],
        default="weekly",
        help="Chart interval to analyse (default: weekly)",
    )
    parser.add_argument(
        "--index",
        choices=sorted(INDEX_LISTS),
        default="nifty100",
        help="Stock index to scan (default: nifty100)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        metavar="N",
        help="Number of calendar days of history to fetch (default: 365)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        dest="log_level",
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        dest="no_telegram",
        help="Skip sending results to Telegram even if TELEGRAM_TOKEN/CHAT_ID are set",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    interval = _MODE_TO_INTERVAL[args.mode]

    telegram_token = None if args.no_telegram else os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = None if args.no_telegram else os.environ.get("TELEGRAM_CHAT_ID")

    analyser = FollowTheFootPrints(
        time_delta_days=args.days,
        index=args.index,
        interval=interval,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
    )
    analyser.process()


if __name__ == "__main__":
    main(sys.argv[1:])
