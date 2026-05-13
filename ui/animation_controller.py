"""Dispatches per-command GIF animations to OctopusWidget."""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QMovie

from config import Config

logger = logging.getLogger(__name__)

ANIMATIONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "animations"


class AnimationController:
    """Loads GIF animations from assets/animations/ and plays them on command fire.

    Falls back to the octopus 'processing' state + 1.2s timer when no animation
    is configured for a command, preserving existing behaviour exactly.
    """

    def __init__(self, config: Config, octopus) -> None:
        self._config = config
        self._octopus = octopus
        self._cache: dict[str, QMovie] = {}
        self._fallback_timer = QTimer()
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self._return_to_idle)
        octopus.animation_finished.connect(self._return_to_idle)

    def on_command(self, name: str) -> None:
        action = self._config.commands.get(name)
        animation_stem = action.animation if action else None

        if animation_stem:
            movie = self._load_gif(animation_stem)
            if movie is not None:
                logger.debug("Playing animation %r for command %r", animation_stem, name)
                self._octopus.play_animation(movie)
                return

        logger.debug("No animation for %r — using processing state", name)
        self._octopus.set_state("processing")
        self._fallback_timer.start(1200)

    def _load_gif(self, stem: str) -> QMovie | None:
        if stem in self._cache:
            movie = self._cache[stem]
            movie.stop()
            movie.jumpToFrame(0)
            return movie

        path = ANIMATIONS_DIR / f"{stem}.gif"
        if not path.exists():
            logger.debug("Animation file not found: %s", path)
            return None

        movie = QMovie(str(path))
        if not movie.isValid():
            logger.warning("Invalid GIF file: %s", path)
            return None

        self._cache[stem] = movie
        return movie

    def _return_to_idle(self) -> None:
        self._octopus.set_state("idle")
