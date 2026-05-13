"""DAW control action (stub — MIDI/OSC not yet implemented)."""
from __future__ import annotations

import logging
from typing import ClassVar

from actions.base import Action

logger = logging.getLogger(__name__)


class DawAction(Action):
    action_type: ClassVar[str] = "daw"

    def __init__(self, name: str, track: str, command: str, animation: str | None = None):
        super().__init__(name, animation)
        self.track = track
        self.command = command

    def execute(self, dry_run: bool = False) -> None:
        logger.warning("DAW action not yet implemented (track=%r command=%r)", self.track, self.command)

    @classmethod
    def from_config(cls, name: str, data: dict) -> DawAction:
        if "track" not in data or "command" not in data:
            raise ValueError(f"DAW command {name!r} missing 'track' or 'command' field")
        return cls(
            name=name,
            track=data["track"],
            command=data["command"],
            animation=data.get("animation"),
        )

    def summary(self) -> str:
        return f"[daw] {self.command} on {self.track}"


from actions import register  # noqa: E402
register(DawAction)
