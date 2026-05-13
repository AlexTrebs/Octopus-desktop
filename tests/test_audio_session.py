"""Tests for AudioSession.resample() and _find_default_device()."""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


def _make_session(native_rate):
    from audio_session import AudioSession
    return AudioSession(
        pa=MagicMock(), stream=MagicMock(), processor=MagicMock(),
        native_rate=native_rate, read_size=512,
    )


# --- AudioSession.resample ---

def test_resample_passthrough_at_native_rate():
    from audio_processor import SAMPLE_RATE
    session = _make_session(SAMPLE_RATE)
    pcm = np.array([100, 200, 300], dtype=np.int16)
    result = session.resample(pcm)
    assert np.array_equal(result, pcm)


def test_resample_downsamples_correctly():
    from audio_processor import SAMPLE_RATE
    session = _make_session(48000)
    pcm = np.ones(480, dtype=np.int16)
    result = session.resample(pcm)
    expected_len = int(480 * SAMPLE_RATE / 48000)
    assert len(result) == expected_len


def test_resample_output_dtype_is_int16():
    session = _make_session(48000)
    result = session.resample(np.ones(480, dtype=np.int16))
    assert result.dtype == np.int16


def test_resample_is_contiguous():
    session = _make_session(48000)
    result = session.resample(np.ones(480, dtype=np.int16))
    assert result.flags["C_CONTIGUOUS"]


# --- _find_default_device ---

def _make_pa(devices: list[dict]) -> MagicMock:
    """Build a mock PyAudio with a list of device dicts."""
    pa = MagicMock()
    pa.get_device_count.return_value = len(devices)
    pa.get_device_info_by_index.side_effect = lambda i: devices[i]
    return pa


def test_find_default_device_picks_default():
    from audio_session import _find_default_device
    pa = _make_pa([
        {"name": "hw:1,0", "maxInputChannels": 1},
        {"name": "default", "maxInputChannels": 1},
    ])
    assert _find_default_device(pa) == 1


def test_find_default_device_picks_pulse_when_no_default():
    from audio_session import _find_default_device
    pa = _make_pa([{"name": "pulse", "maxInputChannels": 1}])
    assert _find_default_device(pa) == 0


def test_find_default_device_returns_none_when_no_preferred():
    from audio_session import _find_default_device
    pa = _make_pa([{"name": "hw:1,0", "maxInputChannels": 1}])
    assert _find_default_device(pa) is None


# --- _open_stream fallback logic ---

def test_open_stream_step1_succeeds_at_16khz():
    from audio_session import _open_stream
    from audio_processor import SAMPLE_RATE
    pa = MagicMock()
    pa.get_device_info_by_index.return_value = {"name": "mic"}
    mock_stream = MagicMock()
    pa.open.return_value = mock_stream
    stream, rate, size = _open_stream(pa, 0, 512)
    assert stream is mock_stream
    assert rate == SAMPLE_RATE
    assert size == 512


def test_open_stream_step2_default_device_fallback():
    from audio_session import _open_stream
    from audio_processor import SAMPLE_RATE
    pa = MagicMock()
    pa.get_device_info_by_index.return_value = {"name": "usb-mic", "defaultSampleRate": 48000.0}
    mock_stream = MagicMock()
    pa.open.side_effect = [Exception("16kHz fail"), mock_stream]
    with patch("audio_session._find_default_device", return_value=99):
        stream, rate, size = _open_stream(pa, 0, 512)
    assert stream is mock_stream
    assert rate == SAMPLE_RATE


def test_open_stream_step3_native_rate_fallback():
    from audio_session import _open_stream
    pa = MagicMock()
    pa.get_device_info_by_index.return_value = {"name": "usb-mic", "defaultSampleRate": 48000.0}
    mock_stream = MagicMock()
    # Step 1 fails, Step 2 (default) has no fallback device → goes to Step 3
    pa.open.side_effect = [Exception("16kHz fail"), mock_stream]
    with patch("audio_session._find_default_device", return_value=None):
        stream, rate, size = _open_stream(pa, 0, 512)
    assert stream is mock_stream
    assert rate == 48000


def test_open_stream_all_fail_raises():
    from audio_session import _open_stream
    pa = MagicMock()
    pa.get_device_info_by_index.return_value = {"name": "mic", "defaultSampleRate": 48000.0}
    pa.open.side_effect = Exception("always fails")
    with patch("audio_session._find_default_device", return_value=None):
        with pytest.raises(RuntimeError, match="Could not open"):
            _open_stream(pa, 0, 512)


# --- open_audio_session context manager ---

def test_open_audio_session_yields_session_and_cleans_up():
    from audio_session import open_audio_session
    mock_pa = MagicMock()
    mock_stream = MagicMock()
    mock_processor = MagicMock()

    with (
        patch("audio_session.AudioProcessor", return_value=mock_processor),
        patch("audio_session.create_pyaudio", return_value=mock_pa),
        patch("audio_session.pick_input_device", return_value=0),
        patch("audio_session._open_stream", return_value=(mock_stream, 16000, 512)),
    ):
        from config import Config
        cfg = MagicMock(spec=Config)
        cfg.environment = MagicMock()
        cfg.enable_audio_processing = True
        with open_audio_session(cfg) as session:
            assert session.stream is mock_stream
            assert session.processor is mock_processor
            assert session.native_rate == 16000

    mock_stream.stop_stream.assert_called_once()
    mock_stream.close.assert_called_once()
    mock_pa.terminate.assert_called_once()
