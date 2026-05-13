"""Base class for all action types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class Action(ABC):
    action_type: ClassVar[str]

    def __init__(self, name: str, animation: str | None = None):
        self.name = name
        self.animation = animation

    @abstractmethod
    def execute(self, dry_run: bool = False) -> None: ...

    @classmethod
    @abstractmethod
    def from_config(cls, name: str, data: dict) -> "Action": ...

    @abstractmethod
    def summary(self) -> str: ...
