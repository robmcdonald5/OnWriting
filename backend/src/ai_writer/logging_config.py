"""Structured logging configuration for the ai_writer pipeline.

Replaces scattered print() calls with a proper logger hierarchy.
All modules under ai_writer use loggers named "ai_writer.<module>".
"""

import logging
import os
import sys


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure the ai_writer logger hierarchy.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional file path to write logs alongside console output.
    """
    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    root = logging.getLogger("ai_writer")
    root.setLevel(getattr(logging, level))

    # Prevent duplicate handlers on repeated calls
    if not root.handlers:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        root.addHandler(stdout_handler)

    if log_file:
        resolved = os.path.abspath(log_file)
        # Check if we already have a file handler for this path
        for h in root.handlers:
            if isinstance(h, logging.FileHandler) and h.baseFilename == resolved:
                return
        file_handler = logging.FileHandler(resolved)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
