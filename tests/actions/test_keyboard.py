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
