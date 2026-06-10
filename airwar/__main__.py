"""Command-line entry point for AirWar."""

from __future__ import annotations

import argparse
import logging

from airwar._log import LOGGER_NAME, install_crash_hook, setup_logging
from airwar.game import Game


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airwar",
        description="AirWar -- 2D space shooter",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging to ~/.cache/airwar/airwar.log and crash dumps.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    setup_logging(debug=args.debug)
    logger = logging.getLogger(LOGGER_NAME)
    logger.debug("AirWar starting (debug=%s)", args.debug)
    install_crash_hook(extra_context={"debug": args.debug})
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
