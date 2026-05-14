"""Logging setup for the voice assistant."""

import logging
import sys
from datetime import datetime


def setup(log_level: str = "INFO") -> None:
    """Configure the root logger."""
    level = getattr(logging, log_level, None)
    if not isinstance(level, int):
        level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d] %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


def timestamp() -> str:
    """Format current time as [HH:MM:SS.mmm] for console UI output."""
    now = datetime.now()
    return now.strftime("[%H:%M:%S.") + f"{now.microsecond // 1000:03d}]"
