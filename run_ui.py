#!/usr/bin/env python3
"""Launch Octopus Voice Assistant with PyQt6 GUI."""

import sys
from pathlib import Path

# Add src/ and ui/ to the import path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "ui"))

import log
from config import Config, ConfigError

def main():
    try:
        config = Config()
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    log.setup(log_level=config.log_level)

    try:
        config.validate()
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    from app import run_gui
    run_gui(config)


if __name__ == "__main__":
    main()
