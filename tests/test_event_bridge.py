"""Tests for AssistantSignals and AudioWorkerThread._on_event routing."""
import pytest
from unittest.mock import MagicMock


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
