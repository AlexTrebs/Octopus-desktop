"""Octopus Voice Assistant — entry point."""

import argparse
import logging
import signal
import sys
import threading

import numpy as np

import log
from assistant import VoiceAssistant
from audio_session import open_audio_session
from config import (
    Config,
    ConfigError,
    PROJECT_ROOT,
    VOSK_DOWNLOAD_HINT,
    CHUNK_SIZE,
)

logger = logging.getLogger(__name__)

BANNER = r"""
   ____       __
  / __ \___  / /____  ____  __  _______
 / / / / __|/ __/ _ \/ __ \/ / / / ___/
/ /_/ / /_ / /_/ (_) / /_/ / /_/ (__  )
\____/\___/ \__/\___/ .___/\__,_/____/
                   /_/
  Voice Assistant v1.0
"""


def run_normal(config: Config) -> None:
    mode = "Porcupine + Vosk" if config.use_porcupine else "Vosk"
    logger.debug("Mode: %s, Commands: %d", mode, len(config.command_names()))

    shutdown_event = threading.Event()

    def handle_shutdown(_signum, _frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    with open_audio_session(config) as session:
        assistant = VoiceAssistant(config, session.processor)
        logger.info("Listening for '%s'...", config.wake_word)

        try:
            while not shutdown_event.is_set():
                try:
                    raw = session.stream.read(session.read_size, exception_on_overflow=False)
                except IOError as e:
                    logger.debug("Audio read error: %s", e)
                    continue

                pcm = np.frombuffer(raw, dtype=np.int16)
                pcm = session.resample(pcm)
                assistant.process_audio(pcm)

        finally:
            assistant.cleanup()
            logger.info("Stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Octopus Voice Assistant - voice-controlled live performance tool",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (check mic, detection, dry-run commands)",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Run in listen mode (transcribe all speech to console)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch with PyQt6 desktop GUI",
    )
    args = parser.parse_args()

    print(BANNER)

    print("Loading configuration...")
    try:
        config = Config()
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    log.setup(log_level=config.log_level)

    if args.gui:
        import sys as _sys
        from pathlib import Path as _Path
        _ui_dir = str(_Path(__file__).resolve().parent.parent / "ui")
        if _ui_dir not in _sys.path:
            _sys.path.insert(0, _ui_dir)
        try:
            config.validate()
        except ConfigError as e:
            print(f"Error: {e}")
            sys.exit(1)

        from app import run_gui
        run_gui(config)
        return

    if args.listen:
        try:
            config.validate()
        except ConfigError as e:
            print(f"Error: {e}")
            sys.exit(1)
        config.print_summary()

        from listen_mode import run_listen

        run_listen(config)
    elif args.test:
        try:
            config.validate()
        except ConfigError as e:
            print(f"Error: {e}")
            sys.exit(1)
        config.print_summary()

        from test_mode import run_test

        run_test(config)
    else:
        try:
            config.validate()
        except ConfigError as e:
            print(f"Error: {e}")
            sys.exit(1)
        config.print_summary()
        run_normal(config)


if __name__ == "__main__":
    main()
