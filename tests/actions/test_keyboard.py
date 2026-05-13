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


def test_keyboard_execute_live_presses_and_releases():
    from actions.keyboard import KeyboardAction
    from unittest.mock import patch, MagicMock
    action = KeyboardAction.from_config("x", {"action": "keyboard", "keys": [["F5"]]})
    mock_ctrl = MagicMock()
    with patch("actions.keyboard._keyboard", mock_ctrl):
        action.execute(dry_run=False)
    assert mock_ctrl.press.called
    assert mock_ctrl.release.called


def test_keyboard_execute_multi_chord_sleeps_between():
    from actions.keyboard import KeyboardAction
    from unittest.mock import patch, MagicMock
    action = KeyboardAction.from_config("x", {
        "action": "keyboard",
        "keys": [["Control", "c"], ["Control", "v"]],
    })
    mock_ctrl = MagicMock()
    with patch("actions.keyboard._keyboard", mock_ctrl):
        with patch("actions.keyboard.time.sleep") as mock_sleep:
            action.execute(dry_run=False)
    # Sleep between chords but NOT after the last
    assert mock_sleep.call_count == 1


def test_keyboard_from_config_invalid_keys_format():
    from actions.keyboard import KeyboardAction
    with pytest.raises(ValueError, match="list of lists"):
        KeyboardAction.from_config("bad", {"action": "keyboard", "keys": ["F5"]})
