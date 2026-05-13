"""Tests for audio device selection utilities."""
from unittest.mock import MagicMock, patch


def _make_pa(devices: list[dict]) -> MagicMock:
    pa = MagicMock()
    pa.get_device_count.return_value = len(devices)
    pa.get_device_info_by_index.side_effect = lambda i: devices[i]
    return pa


def test_get_input_devices_filters_output_only():
    from audio_devices import get_input_devices
    pa = _make_pa([
        {"name": "speaker", "maxInputChannels": 0},
        {"name": "microphone", "maxInputChannels": 1},
    ])
    devices = get_input_devices(pa)
    assert len(devices) == 1
    assert devices[0]["description"] == "microphone"


def test_get_input_devices_empty_when_none():
    from audio_devices import get_input_devices
    pa = _make_pa([{"name": "speaker", "maxInputChannels": 0}])
    assert get_input_devices(pa) == []


def test_get_input_devices_returns_index_and_description():
    from audio_devices import get_input_devices
    pa = _make_pa([{"name": "mic", "maxInputChannels": 2}])
    devices = get_input_devices(pa)
    assert devices[0]["index"] == 0
    assert devices[0]["description"] == "mic"


def test_get_input_devices_multiple_inputs():
    from audio_devices import get_input_devices
    pa = _make_pa([
        {"name": "mic1", "maxInputChannels": 1},
        {"name": "mic2", "maxInputChannels": 2},
    ])
    assert len(get_input_devices(pa)) == 2


def test_is_loopback_detects_monitor():
    from audio_devices import _is_loopback
    assert _is_loopback("Monitor of Built-in Audio") is True
    assert _is_loopback("monitor") is True
    assert _is_loopback("MONITOR_OUTPUT") is True


def test_is_loopback_returns_false_for_real_device():
    from audio_devices import _is_loopback
    assert _is_loopback("Built-in Microphone") is False
    assert _is_loopback("USB Audio") is False
    assert _is_loopback("default") is False


# --- create_pyaudio ---

def test_create_pyaudio_returns_pa_instance():
    import pyaudio
    mock_pa = MagicMock(spec=pyaudio.PyAudio)
    with patch("audio_devices.pyaudio.PyAudio", return_value=mock_pa):
        from audio_devices import create_pyaudio
        result = create_pyaudio()
    assert result is mock_pa


# --- _prompt_choice ---

def test_prompt_choice_returns_valid_int():
    from audio_devices import _prompt_choice
    with patch("builtins.input", return_value="2"):
        assert _prompt_choice(3) == 2


def test_prompt_choice_retries_on_invalid_string():
    from audio_devices import _prompt_choice
    inputs = iter(["abc", "1"])
    with patch("builtins.input", side_effect=lambda *a, **kw: next(inputs)):
        assert _prompt_choice(2) == 1


def test_prompt_choice_retries_on_out_of_range():
    from audio_devices import _prompt_choice
    inputs = iter(["0", "99", "2"])
    with patch("builtins.input", side_effect=lambda *a, **kw: next(inputs)):
        assert _prompt_choice(3) == 2


# --- pick_input_device ---

def test_pick_input_device_single_device():
    from audio_devices import pick_input_device
    pa = MagicMock()
    with patch("audio_devices.get_input_devices", return_value=[{"index": 3, "description": "mic"}]):
        result = pick_input_device(pa)
    assert result == 3


def test_pick_input_device_multiple_devices_prompts():
    from audio_devices import pick_input_device
    pa = MagicMock()
    devices = [
        {"index": 0, "description": "mic"},
        {"index": 1, "description": "loopback monitor"},
    ]
    with patch("audio_devices.get_input_devices", return_value=devices):
        with patch("audio_devices._prompt_choice", return_value=1):
            result = pick_input_device(pa)
    assert result == 0  # first in ordered list


def test_pick_input_device_no_devices_exits():
    import pytest
    from audio_devices import pick_input_device
    pa = MagicMock()
    with patch("audio_devices.get_input_devices", return_value=[]):
        with pytest.raises(SystemExit):
            pick_input_device(pa)


def test_prompt_choice_keyboard_interrupt_exits():
    import pytest
    from audio_devices import _prompt_choice
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit):
            _prompt_choice(3)
