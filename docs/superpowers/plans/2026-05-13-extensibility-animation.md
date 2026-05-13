# Extensibility & Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic action type system with a discoverable plugin architecture and add per-command GIF animations driven by a new AnimationController.

**Architecture:** Action types move into `src/actions/` as self-contained files that self-register into a central registry. `Config` calls `actions.build()` to construct actions from JSON. A new `AnimationController` in `ui/` sits between `AssistantSignals` and `OctopusWidget`, loading GIFs from `assets/animations/` on command fire.

**Tech Stack:** Python 3.12, PyQt6, pynput, pytest

---

## File Map

| File | Status | Purpose |
|---|---|---|
| `src/actions/__init__.py` | CREATE | Registry: `register`, `load_all`, `build` |
| `src/actions/base.py` | CREATE | `Action` ABC with `execute`, `from_config`, `summary`, `animation` |
| `src/actions/keyboard.py` | CREATE | `KeyboardAction` + `parse_key` + `_KEY_MAP` (moved from `command_executor.py`) |
| `src/actions/daw.py` | CREATE | `DawAction` stub |
| `src/actions/none.py` | CREATE | `NoneAction` |
| `src/command_executor.py` | DELETE | Logic absorbed by action classes |
| `src/config.py` | MODIFY | Remove old types, call `actions.build()`, update `validate()` |
| `src/assistant.py` | MODIFY | Call `action.execute()` directly, update log line |
| `src/test_mode.py` | MODIFY | Update `_test_command_execution` |
| `ui/animation_controller.py` | CREATE | Load GIFs, dispatch command → animation |
| `ui/octopus_widget.py` | MODIFY | Add `set_audio_level`, `play_animation`, `animation_finished` signal |
| `ui/main_window.py` | MODIFY | Wire `AnimationController`, update `_on_command` and `_on_audio_level` |
| `assets/animations/.gitkeep` | CREATE | Establishes the animations folder |
| `tests/conftest.py` | CREATE | Add `src/` and `ui/` to `sys.path` |
| `tests/actions/test_registry.py` | CREATE | Registry discovery and build tests |
| `tests/actions/test_keyboard.py` | CREATE | `parse_key` and `KeyboardAction.from_config` tests |
| `tests/actions/test_actions.py` | CREATE | `DawAction`, `NoneAction`, animation field tests |
| `pytest.ini` | CREATE | Test configuration |

---

## Task 1: Test Infrastructure + Action ABC

**Files:**
- Create: `pytest.ini`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`
- Create: `tests/actions/__init__.py`
- Create: `src/actions/__init__.py` (stub only — flesh out in Task 4)
- Create: `src/actions/base.py`

- [ ] **Step 1: Add pytest to requirements and create pytest.ini**

Append to `requirements.txt`:
```
pytest>=8.0.0
```

Create `pytest.ini` at project root:
```ini
[pytest]
testpaths = tests
```

- [ ] **Step 2: Create test path config**

Create `tests/__init__.py` (empty) and `tests/actions/__init__.py` (empty).

Create `tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))
```

- [ ] **Step 3: Write failing test for Action ABC**

Create `tests/actions/test_base.py`:
```python
import pytest
from actions.base import Action


def test_action_is_abstract():
    with pytest.raises(TypeError):
        Action(name="test")


def test_concrete_action_requires_execute():
    class NoExecute(Action):
        action_type = "test"
        def from_config(cls, name, data): ...
        def summary(self): return ""

    with pytest.raises(TypeError):
        NoExecute(name="test")
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd /home/alextrebs/Workspace/Octopus-desktop
uv run pytest tests/actions/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'actions'`

- [ ] **Step 5: Create stub `src/actions/__init__.py`**

```python
"""Action plugin registry."""
from __future__ import annotations
```

- [ ] **Step 6: Create `src/actions/base.py`**

```python
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
    def from_config(cls, name: str, data: dict) -> Action: ...

    @abstractmethod
    def summary(self) -> str: ...
```

- [ ] **Step 7: Run test to verify it passes**

```bash
uv run pytest tests/actions/test_base.py -v
```

Expected: 2 PASSED

- [ ] **Step 8: Commit**

```bash
git add pytest.ini requirements.txt tests/ src/actions/
git commit -m "feat: add test infrastructure and Action ABC"
```

---

## Task 2: KeyboardAction

**Files:**
- Create: `src/actions/keyboard.py`
- Create: `tests/actions/test_keyboard.py`

- [ ] **Step 1: Write failing tests**

Create `tests/actions/test_keyboard.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from pynput.keyboard import Key, KeyCode


def test_parse_key_special():
    from actions.keyboard import parse_key
    assert parse_key("Control") == Key.ctrl
    assert parse_key("Shift") == Key.shift
    assert parse_key("F5") == Key.f5
    assert parse_key("Return") == Key.enter
    assert parse_key("MediaPlayPause") == Key.media_play_pause


def test_parse_key_single_char():
    from actions.keyboard import parse_key
    result = parse_key("c")
    assert isinstance(result, KeyCode)


def test_parse_key_invalid():
    from actions.keyboard import parse_key
    with pytest.raises(ValueError, match="Unknown key name"):
        parse_key("NotARealKey")


def test_keyboard_from_config_valid():
    from actions.keyboard import KeyboardAction
    action = KeyboardAction.from_config("start", {"action": "keyboard", "keys": [["F5"]]})
    assert action.name == "start"
    assert action.keys == [["F5"]]
    assert action.animation is None


def test_keyboard_from_config_with_animation():
    from actions.keyboard import KeyboardAction
    action = KeyboardAction.from_config(
        "start", {"action": "keyboard", "keys": [["F5"]], "animation": "start_anim"}
    )
    assert action.animation == "start_anim"


def test_keyboard_from_config_missing_keys():
    from actions.keyboard import KeyboardAction
    with pytest.raises(ValueError, match="missing 'keys'"):
        KeyboardAction.from_config("bad", {"action": "keyboard"})


def test_keyboard_from_config_invalid_key_name():
    from actions.keyboard import KeyboardAction
    with pytest.raises(ValueError, match="invalid key"):
        KeyboardAction.from_config("bad", {"action": "keyboard", "keys": [["NotAKey"]]})


def test_keyboard_summary():
    from actions.keyboard import KeyboardAction
    action = KeyboardAction.from_config("x", {"action": "keyboard", "keys": [["Control", "c"], ["Control", "v"]]})
    assert action.summary() == "[keyboard] Control+c -> Control+v"


def test_keyboard_execute_dry_run(capsys):
    from actions.keyboard import KeyboardAction
    action = KeyboardAction.from_config("x", {"action": "keyboard", "keys": [["F5"]]})
    action.execute(dry_run=True)
    out = capsys.readouterr().out
    assert "F5" in out
    assert "dry-run" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/actions/test_keyboard.py -v
```

Expected: `ModuleNotFoundError: No module named 'actions.keyboard'`

- [ ] **Step 3: Create `src/actions/keyboard.py`**

```python
"""Keyboard shortcut action — simulates key presses via pynput."""
from __future__ import annotations

import logging
import platform
import time
from typing import ClassVar

from pynput.keyboard import Controller, Key, KeyCode

from actions.base import Action

logger = logging.getLogger(__name__)

_keyboard = Controller()

_KEY_MAP: dict[str, Key] = {
    "MediaPlayPause": Key.media_play_pause,
    "MediaNextTrack": Key.media_next,
    "MediaPreviousTrack": Key.media_previous,
    "VolumeUp": Key.media_volume_up,
    "VolumeMute": Key.media_volume_mute,
    "VolumeDown": Key.media_volume_down,
    "Control": Key.ctrl,
    "Ctrl": Key.ctrl,
    "Shift": Key.shift,
    "Alt": Key.alt,
    "AltGr": Key.alt_gr,
    "F1": Key.f1, "F2": Key.f2, "F3": Key.f3, "F4": Key.f4,
    "F5": Key.f5, "F6": Key.f6, "F7": Key.f7, "F8": Key.f8,
    "F9": Key.f9, "F10": Key.f10, "F11": Key.f11, "F12": Key.f12,
    "Escape": Key.esc, "Esc": Key.esc,
    "Tab": Key.tab,
    "Space": Key.space,
    "Return": Key.enter, "Enter": Key.enter,
    "Backspace": Key.backspace,
    "Delete": Key.delete,
    "Home": Key.home, "End": Key.end,
    "PageUp": Key.page_up, "PageDown": Key.page_down,
    "Up": Key.up, "Down": Key.down, "Left": Key.left, "Right": Key.right,
    "Insert": Key.insert,
    "PrintScreen": Key.print_screen,
    "ScrollLock": Key.scroll_lock,
    "Pause": Key.pause,
    "CapsLock": Key.caps_lock,
    "NumLock": Key.num_lock,
    "Menu": Key.menu,
}

_system = platform.system()
if _system == "Darwin":
    _KEY_MAP.update({"Command": Key.cmd, "Meta": Key.cmd, "Windows": Key.cmd})
elif _system == "Windows":
    _KEY_MAP.update({"Windows": Key.cmd, "Meta": Key.cmd, "Command": Key.ctrl})
else:
    _KEY_MAP.update({"Meta": Key.cmd, "Super": Key.cmd, "Windows": Key.cmd, "Command": Key.ctrl})


def parse_key(key_name: str) -> Key | KeyCode:
    if key_name in _KEY_MAP:
        return _KEY_MAP[key_name]
    if len(key_name) == 1:
        return KeyCode.from_char(key_name.lower())
    raise ValueError(
        f"Unknown key name: {key_name!r}. "
        f"Valid special keys: {', '.join(sorted(_KEY_MAP))}. "
        f"Single characters like 'a', 'b', 'c' are also valid."
    )


class KeyboardAction(Action):
    action_type: ClassVar[str] = "keyboard"

    def __init__(self, name: str, keys: list[list[str]], animation: str | None = None):
        super().__init__(name, animation)
        self.keys = keys

    def execute(self, dry_run: bool = False) -> None:
        for chord in self.keys:
            chord_str = "+".join(chord)
            logger.debug("Pressing: %s", chord_str)
            if dry_run:
                print(f"    [dry-run] {chord_str}")
                continue
            parsed = [parse_key(k) for k in chord]
            for key in parsed:
                _keyboard.press(key)
            for key in reversed(parsed):
                _keyboard.release(key)
            time.sleep(0.05)

    @classmethod
    def from_config(cls, name: str, data: dict) -> KeyboardAction:
        keys = data.get("keys")
        if keys is None:
            raise ValueError(f"Keyboard command {name!r} missing 'keys' field")
        if not isinstance(keys, list) or not all(
            isinstance(chord, list) and all(isinstance(k, str) for k in chord)
            for chord in keys
        ):
            raise ValueError(
                f"Command {name!r} 'keys' must be a list of lists of strings, "
                f'e.g. [["Control", "c"]]'
            )
        for chord in keys:
            for key_name in chord:
                try:
                    parse_key(key_name)
                except ValueError as e:
                    raise ValueError(f"Command {name!r} has invalid key: {e}") from e
        return cls(name=name, keys=keys, animation=data.get("animation"))

    def summary(self) -> str:
        keys_str = " -> ".join("+".join(chord) for chord in self.keys)
        return f"[keyboard] {keys_str}"


from actions import register  # noqa: E402
register(KeyboardAction)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/actions/test_keyboard.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/actions/keyboard.py tests/actions/test_keyboard.py
git commit -m "feat: add KeyboardAction plugin with parse_key"
```

---

## Task 3: DawAction + NoneAction

**Files:**
- Create: `src/actions/daw.py`
- Create: `src/actions/none.py`
- Create: `tests/actions/test_actions.py`

- [ ] **Step 1: Write failing tests**

Create `tests/actions/test_actions.py`:
```python
import pytest


def test_daw_from_config_valid():
    from actions.daw import DawAction
    action = DawAction.from_config("rec", {"action": "daw", "track": "drums", "command": "record"})
    assert action.name == "rec"
    assert action.track == "drums"
    assert action.command == "record"
    assert action.animation is None


def test_daw_from_config_with_animation():
    from actions.daw import DawAction
    action = DawAction.from_config(
        "rec", {"action": "daw", "track": "drums", "command": "record", "animation": "rec_anim"}
    )
    assert action.animation == "rec_anim"


def test_daw_from_config_missing_fields():
    from actions.daw import DawAction
    with pytest.raises(ValueError, match="missing"):
        DawAction.from_config("bad", {"action": "daw", "track": "drums"})


def test_daw_summary():
    from actions.daw import DawAction
    action = DawAction.from_config("rec", {"action": "daw", "track": "drums", "command": "record"})
    assert action.summary() == "[daw] record on drums"


def test_none_from_config():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    assert action.name == "cancel"
    assert action.animation is None


def test_none_from_config_with_animation():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none", "animation": "wave"})
    assert action.animation == "wave"


def test_none_summary():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    assert action.summary() == "[none]"


def test_none_execute_does_not_raise():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    action.execute()
    action.execute(dry_run=True)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/actions/test_actions.py -v
```

Expected: `ModuleNotFoundError: No module named 'actions.daw'`

- [ ] **Step 3: Create `src/actions/daw.py`**

```python
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
```

- [ ] **Step 4: Create `src/actions/none.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/actions/test_actions.py -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add src/actions/daw.py src/actions/none.py tests/actions/test_actions.py
git commit -m "feat: add DawAction and NoneAction plugins"
```

---

## Task 4: Action Registry

**Files:**
- Modify: `src/actions/__init__.py`
- Create: `tests/actions/test_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/actions/test_registry.py`:
```python
import pytest


def test_load_all_registers_builtins():
    import actions
    actions._REGISTRY.clear()
    actions.load_all()
    assert "keyboard" in actions._REGISTRY
    assert "daw" in actions._REGISTRY
    assert "none" in actions._REGISTRY


def test_build_keyboard():
    import actions
    actions.load_all()
    action = actions.build("start", {"action": "keyboard", "keys": [["F5"]]})
    from actions.keyboard import KeyboardAction
    assert isinstance(action, KeyboardAction)
    assert action.name == "start"


def test_build_none_default():
    import actions
    actions.load_all()
    action = actions.build("cancel", {"action": "none"})
    from actions.none import NoneAction
    assert isinstance(action, NoneAction)


def test_build_unknown_raises():
    import actions
    actions.load_all()
    with pytest.raises(ValueError, match="Unknown action type"):
        actions.build("x", {"action": "does_not_exist"})


def test_build_preserves_animation():
    import actions
    actions.load_all()
    action = actions.build("start", {"action": "keyboard", "keys": [["F5"]], "animation": "my_gif"})
    assert action.animation == "my_gif"


def test_load_all_is_idempotent():
    import actions
    actions._REGISTRY.clear()
    actions.load_all()
    actions.load_all()
    assert len([k for k in actions._REGISTRY]) == len(set(actions._REGISTRY))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/actions/test_registry.py -v
```

Expected: `AttributeError: module 'actions' has no attribute 'load_all'`

- [ ] **Step 3: Implement the registry in `src/actions/__init__.py`**

```python
"""Action plugin registry — discovers and constructs action types."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from actions.base import Action

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[Action]] = {}


def register(action_class: type[Action]) -> None:
    _REGISTRY[action_class.action_type] = action_class
    logger.debug("Registered action: %r", action_class.action_type)


def load_all() -> None:
    """Import every .py file in this directory (except base and __init__).

    Each module is expected to call register() at import time.
    Already-imported modules are skipped (importlib returns the cached module).
    """
    actions_dir = Path(__file__).parent
    for path in sorted(actions_dir.glob("*.py")):
        if path.stem in ("__init__", "base"):
            continue
        module_name = f"actions.{path.stem}"
        try:
            importlib.import_module(module_name)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/actions/test_registry.py -v
```

Expected: all PASSED

- [ ] **Step 5: Run full test suite to check nothing broke**

```bash
uv run pytest tests/ -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add src/actions/__init__.py tests/actions/test_registry.py
git commit -m "feat: add action plugin registry with auto-discovery"
```

---

## Task 5: Migrate Config to Use the Registry

**Files:**
- Modify: `src/config.py`

The goal: remove `KeyboardAction`, `DawAction`, `NoneAction`, and `Command` from `config.py`. Wire `_load_commands` to call `actions.load_all()` then `actions.build()`. Update `print_summary` to use `action.summary()`. Remove the `parse_key` validation from `validate()` since `from_config` now handles it.

- [ ] **Step 1: Open `src/config.py` and remove the old type definitions**

Remove these lines entirely (they move to `src/actions/`):
```python
@dataclass
class KeyboardAction:
    name: str
    keys: list[list[str]]


@dataclass
class DawAction:
    name: str
    track: str
    command: str


@dataclass
class NoneAction:
    name: str


Command = KeyboardAction | DawAction | NoneAction
```

- [ ] **Step 2: Replace the `import pyaudio` / dataclass imports section**

Remove `from dataclasses import dataclass` and change the imports block at the top of `config.py` to add:
```python
import actions as _actions
from actions.base import Action
```

The full imports block should now look like:
```python
import json
import logging
import os
from enum import Enum
from pathlib import Path

import actions as _actions
from actions.base import Action
from dotenv import load_dotenv
```

- [ ] **Step 3: Update `Config.commands` type annotation**

Change the type annotation from `dict[str, Command]` to `dict[str, Action]`:
```python
self.commands: dict[str, Action] = self._load_commands(commands_path)
```

- [ ] **Step 4: Rewrite `_load_commands`**

Replace the entire `_load_commands` method with:
```python
def _load_commands(self, path: str) -> dict[str, Action]:
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
```

- [ ] **Step 5: Update `validate()` — remove the `parse_key` import block**

The key validation now happens in `KeyboardAction.from_config()` at load time, so the validation loop is no longer needed. The updated `validate()` should be:
```python
def validate(self) -> None:
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
```

- [ ] **Step 6: Update `print_summary` to use `action.summary()`**

Replace the old `isinstance`-based printing loop:
```python
if self.commands:
    print("\n  Registered commands:")
    for name, action in self.commands.items():
        print(f"    {name:<20} {action.summary()}")
```

- [ ] **Step 7: Update `command_names()` return type annotation**

No code change needed — it already returns `list[self.commands.keys()]`. Just verify it still works.

- [ ] **Step 8: Verify the app boots and loads commands**

```bash
uv run python src/main.py --help
```

Expected: prints help without error.

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from config import Config
c = Config()
c.print_summary()
"
```

Expected: prints config summary with commands listed using `action.summary()` format.

- [ ] **Step 9: Commit**

```bash
git add src/config.py
git commit -m "feat: migrate Config to use action plugin registry"
```

---

## Task 6: Delete command_executor.py, Update assistant.py + test_mode.py

**Files:**
- Delete: `src/command_executor.py`
- Modify: `src/assistant.py`
- Modify: `src/test_mode.py`

- [ ] **Step 1: Update `src/assistant.py` — remove command_executor import**

Remove this line:
```python
from command_executor import execute
```

- [ ] **Step 2: Update the three threading calls in `assistant.py`**

In `_handle_vosk_text`, change:
```python
threading.Thread(target=execute, args=(remainder, command), daemon=True).start()
```
to:
```python
threading.Thread(target=command.execute, daemon=True).start()
```

In `_process_listening`, change:
```python
threading.Thread(target=execute, args=(command_name, command), daemon=True).start()
```
to:
```python
threading.Thread(target=command.execute, daemon=True).start()
```

- [ ] **Step 3: Update the log lines in `assistant.py` to use `action_type`**

In `_handle_vosk_text`, change:
```python
logger.info("Command: %r [%s]", remainder, type(command).__name__)
```
to:
```python
logger.info("Command: %r [%s]", remainder, command.action_type)
```

In `_process_listening`, change:
```python
logger.info("Command: %r [%s] %.0fms after wake word", command_name, type(command).__name__, latency_ms)
```
to:
```python
logger.info("Command: %r [%s] %.0fms after wake word", command_name, command.action_type, latency_ms)
```

- [ ] **Step 4: Update `src/test_mode.py` — remove command_executor import**

Find `_test_command_execution` and replace the entire function:
```python
def _test_command_execution(config: Config) -> None:
    print("\n--- Test 5: Command Execution (dry-run) ---")
    for name, action in config.commands.items():
        print(f"\n  Command: {name!r}")
        action.execute(dry_run=True)
```

- [ ] **Step 5: Delete `src/command_executor.py`**

```bash
git rm src/command_executor.py
```

- [ ] **Step 6: Verify the app still boots cleanly**

```bash
uv run python src/main.py --help
```

Expected: no errors.

- [ ] **Step 7: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all PASSED

- [ ] **Step 8: Commit**

```bash
git add src/assistant.py src/test_mode.py
git commit -m "feat: remove command_executor, actions now own their execute()"
```

---

## Task 7: OctopusWidget — Audio Level Reactivity + GIF Playback

**Files:**
- Modify: `ui/octopus_widget.py`

The octopus widget needs two additions:
1. `set_audio_level(db: float)` — modulates tentacle wave amplitude live
2. `play_animation(movie: QMovie)` + `animation_finished` signal — GIF overlay mode

- [ ] **Step 1: Add `animation_finished` signal and `_movie` field**

At the top of `OctopusWidget.__init__`, after existing field assignments, add:
```python
from PyQt6.QtCore import pyqtSignal
```

Add the signal as a class attribute (before `__init__`):
```python
animation_finished = pyqtSignal()
```

Inside `__init__`, after `self._blink_cooldown = ...`, add:
```python
self._movie: QMovie | None = None
self._live_amplitude: float = 0.0
```

- [ ] **Step 2: Add `set_audio_level` method**

Add after `set_theme`:
```python
def set_audio_level(self, db: float) -> None:
    # Map dB range [-60, 0] to amplitude multiplier [0, 1]
    self._live_amplitude = max(0.0, min(1.0, (db + 60) / 60))
```

- [ ] **Step 3: Use `_live_amplitude` in `_draw_tentacles`**

In `_draw_tentacles`, replace:
```python
wave_amp = 8
if self._state == "listening":
    wave_amp = 12
elif self._state == "processing":
    wave_amp = 16
```
with:
```python
base_amp = {"idle": 8, "listening": 12, "processing": 16}.get(self._state, 8)
wave_amp = base_amp + self._live_amplitude * 10
```

- [ ] **Step 4: Add `play_animation` method**

Add after `set_audio_level`:
```python
def play_animation(self, movie: QMovie) -> None:
    if self._movie is not None:
        self._movie.stop()
    self._movie = movie
    self._movie.frameChanged.connect(self.update)
    self._movie.finished.connect(self._on_animation_finished)
    self._movie.start()

def _on_animation_finished(self) -> None:
    self._movie = None
    self.animation_finished.emit()
    self.update()
```

- [ ] **Step 5: Update `paintEvent` to render GIF frame when active**

Replace the `paintEvent` method:
```python
def paintEvent(self, event) -> None:
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if self._movie is not None:
        pixmap = self._movie.currentPixmap()
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            return

    w = self.width()
    h = self.height()
    size = min(w, h)
    cx = w / 2
    cy = h / 2

    scale = size / 200.0
    painter.translate(cx, cy)
    painter.scale(scale, scale)

    self._draw_glow(painter)
    self._draw_tentacles(painter)
    self._draw_body(painter)
    self._draw_eyes(painter)

    painter.end()
```

- [ ] **Step 6: Add the `QMovie` import at the top of the file**

`QMovie` lives in `PyQt6.QtGui`. Add it to the existing `from PyQt6.QtGui import (...)` block:
```python
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QPainterPath,
    QPen,
    QBrush,
    QMovie,
)
```

Also add `QMovie | None` to the `_movie` field type hint in `__init__`:
```python
self._movie: QMovie | None = None
```

- [ ] **Step 7: Verify the GUI launches**

```bash
uv run python src/main.py --gui
```

Expected: window opens, octopus animates. Tentacles should pulse more when you speak into the mic.

- [ ] **Step 8: Commit**

```bash
git add ui/octopus_widget.py
git commit -m "feat: add audio level reactivity and GIF playback to OctopusWidget"
```

---

## Task 8: AnimationController

**Files:**
- Create: `ui/animation_controller.py`
- Create: `assets/animations/.gitkeep`

- [ ] **Step 1: Create `assets/animations/.gitkeep`**

```bash
mkdir -p assets/animations
touch assets/animations/.gitkeep
```

- [ ] **Step 2: Create `ui/animation_controller.py`**

```python
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
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'ui')
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from animation_controller import AnimationController
print('AnimationController imported OK')
"
```

Expected: `AnimationController imported OK`

- [ ] **Step 4: Commit**

```bash
git add ui/animation_controller.py assets/animations/.gitkeep
git commit -m "feat: add AnimationController for per-command GIF animations"
```

---

## Task 9: Wire AnimationController into MainWindow

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1: Add AnimationController import to `main_window.py`**

Add to imports near the top of `main_window.py`:
```python
from animation_controller import AnimationController
```

- [ ] **Step 2: Construct `AnimationController` in `_build_ui`**

At the end of `_build_ui`, after `self._octopus` is created, add:
```python
self._animation_controller = AnimationController(self._config, self._octopus)
```

- [ ] **Step 3: Update `_on_command`**

Replace:
```python
def _on_command(self, name: str) -> None:
    self._octopus.set_state("processing")
    self._status_label.setText(f"Command: {name}")
    QTimer.singleShot(1200, self._return_to_idle)
```
with:
```python
def _on_command(self, name: str) -> None:
    self._status_label.setText(f"Command: {name}")
    self._animation_controller.on_command(name)
```

- [ ] **Step 4: Update `_on_audio_level`**

Replace:
```python
def _on_audio_level(self, level: float) -> None:
    self._level_meter.set_level(level)
```
with:
```python
def _on_audio_level(self, level: float) -> None:
    self._level_meter.set_level(level)
    self._octopus.set_audio_level(level)
```

- [ ] **Step 5: Verify the full GUI works**

```bash
uv run python src/main.py --gui
```

Expected:
- Window opens, octopus visible
- Speak: tentacles pulse with mic volume in real time
- Say wake word + command: octopus shows processing state (or plays GIF if one is configured)
- After ~1.2s (or GIF end): returns to idle

- [ ] **Step 6: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: wire AnimationController into MainWindow"
```

---

## Task 10: Final Verification + Documentation

**Files:**
- Modify: `assets/animations/.gitkeep` → README note

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all PASSED, no warnings about missing modules.

- [ ] **Step 2: Smoke test all three CLI modes**

```bash
uv run python src/main.py --help
```

```bash
uv run python src/main.py --test
```
Expected: runs 5 test steps, reaches command dry-run, shows `[keyboard]` output.

- [ ] **Step 3: Verify external action drop-in works**

Create `/tmp/test_action.py`:
```python
import sys
sys.path.insert(0, 'src')

from actions.base import Action
from actions import register, build
from typing import ClassVar

class HttpAction(Action):
    action_type: ClassVar[str] = "http"

    def __init__(self, name, url, animation=None):
        super().__init__(name, animation)
        self.url = url

    def execute(self, dry_run=False):
        print(f"[http] POST {self.url}")

    @classmethod
    def from_config(cls, name, data):
        return cls(name=name, url=data["url"])

    def summary(self):
        return f"[http] {self.url}"

register(HttpAction)
action = build("webhook", {"action": "http", "url": "https://example.com"})
print(f"Built: {action.summary()}")
action.execute(dry_run=True)
```

```bash
uv run python /tmp/test_action.py
```

Expected:
```
Built: [http] https://example.com
[http] POST https://example.com
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: final verification of action plugin system and animation"
```
