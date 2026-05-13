"""Action plugin registry — discovers and constructs action types."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from actions.base import Action

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type] = {}


def register(action_class: type) -> None:
    _REGISTRY[action_class.action_type] = action_class
    logger.debug("Registered action: %r", action_class.action_type)


def load_all() -> None:
    """Import every .py file in this directory (except base and __init__).

    Each module is expected to call register() at import time.
    Already-imported modules are re-registered in case the registry was cleared.
    """
    import sys
    actions_dir = Path(__file__).parent
    for path in sorted(actions_dir.glob("*.py")):
        if path.stem in ("__init__", "base"):
            continue
        module_name = f"actions.{path.stem}"
        try:
            mod = importlib.import_module(module_name)
            # Re-register if the module was already cached but registry was cleared
            for attr in vars(mod).values():
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "action_type")
                    and attr.action_type not in _REGISTRY
                ):
                    register(attr)
        except Exception as e:
            logger.warning("Failed to load action module %r: %s", module_name, e)
    logger.debug("Available action types: %s", sorted(_REGISTRY))


def build(name: str, data: dict) -> Action:
    """Construct an Action from a commands.json entry.

    Raises ValueError on unknown action type or invalid config.
    """
    action_type = data.get("action", "none")
    cls = _REGISTRY.get(action_type)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY)) or "none loaded"
        raise ValueError(
            f"Unknown action type {action_type!r} for command {name!r}. "
            f"Available: {available}"
        )
    return cls.from_config(name, data)
