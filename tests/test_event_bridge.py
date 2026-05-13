"""Tests for AssistantSignals and AudioWorkerThread._on_event routing."""
import pytest
from unittest.mock import MagicMock, patch


def test_assistant_signals_has_all_signals(qapp_instance):
    from event_bridge import AssistantSignals
    sigs = AssistantSignals()
    for attr in (
        "wake_word_detected", "command_recognized", "command_timeout",
        "state_changed", "audio_level", "error_occurred", "started", "stopped",
    ):
        assert hasattr(sigs, attr)


def test_on_event_wake_word_emits(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    from assistant import AssistantEvent
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    received = []
    signals.wake_word_detected.connect(lambda: received.append(True))
    worker._on_event(AssistantEvent.WAKE_WORD, {})
    assert received == [True]


def test_on_event_command_emits_name(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    from assistant import AssistantEvent
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    received = []
    signals.command_recognized.connect(lambda name: received.append(name))
    worker._on_event(AssistantEvent.COMMAND, {"name": "start"})
    assert received == ["start"]


def test_on_event_timeout_emits(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    from assistant import AssistantEvent
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    received = []
    signals.command_timeout.connect(lambda: received.append(True))
    worker._on_event(AssistantEvent.TIMEOUT, {})
    assert received == [True]


def test_on_event_state_change_emits_state(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    from assistant import AssistantEvent
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    received = []
    signals.state_changed.connect(lambda s: received.append(s))
    worker._on_event(AssistantEvent.STATE_CHANGE, {"state": "listening"})
    assert received == ["listening"]


def test_on_event_audio_level_emits_level(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    from assistant import AssistantEvent
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    received = []
    signals.audio_level.connect(lambda level: received.append(level))
    worker._on_event(AssistantEvent.AUDIO_LEVEL, {"level": -30.0})
    assert received == pytest.approx([-30.0])


def test_request_stop_sets_event(qapp_instance):
    from event_bridge import AudioWorkerThread, AssistantSignals
    signals = AssistantSignals()
    worker = AudioWorkerThread(MagicMock(), None, signals)
    assert not worker._stop_event.is_set()
    worker.request_stop()
    assert worker._stop_event.is_set()


# --- run() loop ---------------------------------------------------------------

def test_run_session_error_emits_error_occurred_and_stopped(qapp_instance):
    """open_audio_session failure → error_occurred + stopped, no started."""
    from event_bridge import AudioWorkerThread, AssistantSignals
    signals = AssistantSignals()
    errors, stopped = [], []
    signals.error_occurred.connect(errors.append)
    signals.stopped.connect(lambda: stopped.append(True))

    worker = AudioWorkerThread(MagicMock(), None, signals)
    with patch("event_bridge.open_audio_session", side_effect=RuntimeError("no mic")):
        worker.run()

    assert errors == ["no mic"]
    assert stopped == [True]


def test_run_reads_frames_and_stops_cleanly(qapp_instance):
    """run() emits started, reads one frame, exits on stop_event, emits stopped."""
    from event_bridge import AudioWorkerThread, AssistantSignals
    signals = AssistantSignals()
    started, stopped = [], []
    signals.started.connect(lambda: started.append(True))
    signals.stopped.connect(lambda: stopped.append(True))

    worker = AudioWorkerThread(MagicMock(), None, signals)

    def fake_read(n, **kwargs):
        worker._stop_event.set()
        return bytes(n * 2)  # n int16 samples

    mock_session = MagicMock()
    mock_session.stream.read.side_effect = fake_read
    mock_session.read_size = 512
    mock_session.resample.side_effect = lambda x: x

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_session
    mock_ctx.__exit__.return_value = False

    with patch("event_bridge.open_audio_session", return_value=mock_ctx):
        with patch("event_bridge.VoiceAssistant") as MockVA:
            MockVA.return_value.cleanup = MagicMock()
            worker.run()

    assert started == [True]
    assert stopped == [True]
