"""Configuration management — loads config.env and commands.json at startup."""

import json
import logging
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

import actions as _actions
from actions.base import Action

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VOSK_DOWNLOAD_HINT = (
    "Download with: wget https://alphacephei.com/vosk/models/"
    "vosk-model-small-en-gb-0.15.tar.gz && tar xzf vosk-model-small-en-gb-0.15.tar.gz"
)

CHANNELS = 1
FORMAT = 8  # pyaudio.paInt16
CHUNK_SIZE = 512


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


class Environment(Enum):
    QUIET = "Quiet"
    MODERATE = "Moderate"
    LOUD = "Loud"



class Config:
    def __init__(self):
        env_path = PROJECT_ROOT / "config.env"
        if not env_path.exists():
            raise ConfigError(
                f"Configuration file not found: {env_path}\n"
                "Copy config.env.example to config.env and fill in your settings."
            )
        load_dotenv(env_path)

        # Porcupine settings
        self.porcupine_access_key: str = os.getenv("PORCUPINE_ACCESS_KEY", "")
        self.porcupine_model_path: str = os.getenv(
            "PORCUPINE_MODEL_PATH", "octopus_custom.ppn"
        )

        # Vosk settings
        self.vosk_model_path: str = os.getenv(
            "VOSK_MODEL_PATH", "vosk-model-small-en-gb-0.15"
        )

        self.wake_word: str = os.getenv("WAKE_WORD", "octopus")

        env_str = os.getenv("ENVIRONMENT", "Moderate")
        try:
            self.environment = Environment(env_str)
        except ValueError:
            raise ConfigError(
                f"Invalid ENVIRONMENT value: {env_str!r}\n"
                "Valid options: Quiet, Moderate, Loud"
            )

        try:
            self.command_timeout: int = int(os.getenv("COMMAND_TIMEOUT", "3"))
        except ValueError:
            raise ConfigError("COMMAND_TIMEOUT must be an integer")

        self.enable_audio_processing: bool = os.getenv(
            "ENABLE_AUDIO_PROCESSING", "true"
        ).lower() in ("true", "1", "yes")

        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

        commands_path = os.getenv("COMMAND_CONFIG_PATH", "commands.json")
        self.commands: dict[str, Action] = self._load_commands(commands_path)

        # UI settings
        self.theme: str = os.getenv("THEME", "Dark")
        try:
            self.overlay_x: int = int(os.getenv("OVERLAY_X", "-1"))
            self.overlay_y: int = int(os.getenv("OVERLAY_Y", "-1"))
        except ValueError:
            raise ConfigError("OVERLAY_X and OVERLAY_Y must be integers")
        self.overlay_position_preset: str = os.getenv("OVERLAY_POSITION", "top-right")
        self.close_behavior: str = os.getenv("CLOSE_BEHAVIOR", "ask")
        self.input_device_name: str | None = os.getenv("INPUT_DEVICE_NAME") or None

        self._use_porcupine = self._check_porcupine()

    def _check_porcupine(self) -> bool:
        if not self.porcupine_access_key:
            return False
        ppn_path = PROJECT_ROOT / self.porcupine_model_path
        return ppn_path.exists()

    @property
    def use_porcupine(self) -> bool:
        return self._use_porcupine

    def _load_commands(self, path: str) -> dict[str, Action]:
        """Load and validate commands from JSON file."""
        commands_file = PROJECT_ROOT / path
        if not commands_file.exists():
            raise ConfigError(f"Commands file not found: {commands_file}")

        try:
            with open(commands_file) as f:
                raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {commands_file}: {e}")

        if not isinstance(raw, dict):
            raise ConfigError(f"{commands_file} must contain a JSON object at the top level")

        _actions.load_all()

        commands: dict[str, Action] = {}
        for name, data in raw.items():
            if not isinstance(data, dict):
                raise ConfigError(f"Command {name!r} must be a JSON object")
            try:
                commands[name] = _actions.build(name, data)
            except ValueError as e:
                raise ConfigError(str(e)) from e

        return commands

    def command_names(self) -> list[str]:
        return list(self.commands.keys())

    def validate(self) -> None:
        """Validate that required models exist on disk."""
        from rnnoise import rnnoise_available
        if not rnnoise_available:
            raise ConfigError(
                "librnnoise not found. Install with: pacman -S rnnoise  or  apt install librnnoise0"
            )
        vosk_path = PROJECT_ROOT / self.vosk_model_path
        if not vosk_path.exists():
            raise ConfigError(
                f"Vosk model not found: {vosk_path}\n{VOSK_DOWNLOAD_HINT}"
            )
        if not self.commands:
            logger.warning("No commands loaded from commands.json")

    def print_summary(self) -> None:
        print("Configuration:")
        print(f"  Wake word:      {self.wake_word}")
        print(f"  Wake word mode: {'Porcupine' if self.use_porcupine else 'Vosk'}")
        print(f"  Environment:    {self.environment.value}")
        print(f"  Command timeout: {self.command_timeout}s")
        print(f"  Vosk model:     {self.vosk_model_path}")
        print(
            f"  Audio processing: {'enabled' if self.enable_audio_processing else 'disabled'}"
        )
        print(f"  Log level:      {self.log_level}")
        print(f"  Commands loaded: {len(self.commands)}")

        if self.commands:
            print("\n  Registered commands:")
            for name, action in self.commands.items():
                print(f"    {name:<20} {action.summary()}")
        print()


def save_config(config: Config) -> None:
    """Write current Config values back to config.env."""
    env_path = PROJECT_ROOT / "config.env"
    lines = [
        "# Octopus Voice Assistant Configuration",
        "",
        f"PORCUPINE_ACCESS_KEY={config.porcupine_access_key}",
        f"PORCUPINE_MODEL_PATH={config.porcupine_model_path}",
        f"VOSK_MODEL_PATH={config.vosk_model_path}",
        f"WAKE_WORD={config.wake_word}",
        f"ENVIRONMENT={config.environment.value}",
        f"COMMAND_TIMEOUT={config.command_timeout}",
        f"ENABLE_AUDIO_PROCESSING={'true' if config.enable_audio_processing else 'false'}",
        f"LOG_LEVEL={config.log_level}",
        "",
        "# UI settings",
        f"THEME={config.theme}",
        f"OVERLAY_X={config.overlay_x}",
        f"OVERLAY_Y={config.overlay_y}",
        f"OVERLAY_POSITION={config.overlay_position_preset}",
        f"CLOSE_BEHAVIOR={config.close_behavior}",
    ]
    if config.input_device_name:
        lines.append(f"INPUT_DEVICE_NAME={config.input_device_name}")
    lines.append("")
    env_path.write_text("\n".join(lines))
