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

logger = logging.getLogger(__name__)

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
        default=730,
        metavar="N",
        help="Number of calendar days of history to fetch (default: 730 ≈ 2 years)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        dest="log_level",
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        dest="log_file",
        help="Append logs to this file (in addition to stderr); useful for cron",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        dest="no_telegram",
        help="Skip sending results to Telegram even if TELEGRAM_TOKEN/CHAT_ID are set",
    )
    return parser


def _send_failure_alert(
    token: str | None,
    chat_id: str | None,
    index: str,
    mode: str,
) -> None:
    """Best-effort Telegram notification when the run crashes."""
    if not token or not chat_id:
        return
    try:
        import requests

        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": (
                    "\u274c *FTF Scanner Failed*\n\n"
                    f"Index: {index}\nMode: {mode}\n"
                    "Check server logs for details."
                ),
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
    except Exception:
        logger.warning("Could not send failure alert to Telegram")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=handlers,
    )

    interval = _MODE_TO_INTERVAL[args.mode]

    telegram_token = None if args.no_telegram else os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = None if args.no_telegram else os.environ.get("TELEGRAM_CHAT_ID")

    try:
        analyser = FollowTheFootPrints(
            time_delta_days=args.days,
            index=args.index,
            interval=interval,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
        )
        analyser.process()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception:
        logger.exception("Fatal error during analysis")
        _send_failure_alert(telegram_token, telegram_chat_id, args.index, args.mode)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
