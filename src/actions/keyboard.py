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
    _KEY_MAP.update({"Meta": Key.cmd, "Super": Key.cmd, "Windows": Key.cmd})


def parse_key(key_name: str) -> Key | KeyCode:
    if key_name in _KEY_MAP:
        return _KEY_MAP[key_name]
    if len(key_name) == 1:
        return KeyCode.from_char(key_name)
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
        for i, chord in enumerate(self.keys):
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
            if i < len(self.keys) - 1:
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
