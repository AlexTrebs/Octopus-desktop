"""No-op action — acknowledges a command without doing anything."""
from __future__ import annotations

import logging
from typing import ClassVar

from actions.base import Action

logger = logging.getLogger(__name__)


class NoneAction(Action):
    action_type: ClassVar[str] = "none"

    def execute(self, dry_run: bool = False) -> None:
        logger.debug("Command acknowledged (no-op): %s", self.name)

    @classmethod
    def from_config(cls, name: str, data: dict) -> NoneAction:
        return cls(name=name, animation=data.get("animation"))

    def summary(self) -> str:
        return "[none]"


from actions import register  # noqa: E402
register(NoneAction)
