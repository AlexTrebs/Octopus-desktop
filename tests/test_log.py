"""Tests for log.setup() and log.timestamp()."""
import logging
import re
import sys


def test_timestamp_format():
    from log import timestamp
    result = timestamp()
    assert re.match(r'^\[\d{2}:\d{2}:\d{2}\.\d{3}\]$', result)


def test_setup_configures_level():
    from log import setup
    root = logging.getLogger()
    orig_level = root.level
    orig_handlers = root.handlers[:]
    try:
        setup("DEBUG")
        assert root.level == logging.DEBUG
    finally:
        root.setLevel(orig_level)
        root.handlers[:] = orig_handlers


def test_setup_invalid_level_defaults_to_info():
    from log import setup
    root = logging.getLogger()
    orig_level = root.level
    orig_handlers = root.handlers[:]
    try:
        setup("NOTVALID")
        assert root.level == logging.INFO
    finally:
        root.setLevel(orig_level)
        root.handlers[:] = orig_handlers


def test_setup_adds_stdout_handler():
    from log import setup
    root = logging.getLogger()
    orig_handlers = root.handlers[:]
    try:
        setup("WARNING")
        streams = [h.stream for h in root.handlers if isinstance(h, logging.StreamHandler)]
        assert sys.stdout in streams
    finally:
        root.handlers[:] = orig_handlers
