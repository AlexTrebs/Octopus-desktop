"""Action plugin registry."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from actions.base import Action

_REGISTRY: dict[str, type] = {}


def register(action_class: type) -> None:
    _REGISTRY[action_class.action_type] = action_class
