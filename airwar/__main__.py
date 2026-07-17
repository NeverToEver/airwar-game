"""Command-line entry point for AirWar."""

from __future__ import annotations

import argparse
import logging

from airwar._log import LOGGER_NAME, get_log_file_path, install_crash_hook, setup_logging
from airwar.game import Game


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airwar",
        description="AirWar -- 2D space shooter",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose DEBUG logging (the log file is always written).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    setup_logging(debug=args.debug)
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("AirWar starting (debug=%s); log file: %s", args.debug, get_log_file_path())
    install_crash_hook(extra_context={"debug": args.debug})
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
