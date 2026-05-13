"""Tests for VoiceAssistant state machine and event emission."""
import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.use_porcupine = False
    cfg.wake_word = "octopus"
    cfg.command_names.return_value = ["start", "stop"]
    cfg.commands = {
        "start": MagicMock(action_type="keyboard"),
        "stop": MagicMock(action_type="keyboard"),
    }
    cfg.vosk_model_path = "vosk-small"
    cfg.command_timeout = 3
    return cfg


@pytest.fixture
def va(mock_config):
    """VoiceAssistant with Vosk and audio processor mocked out."""
    events = []
    with (
        patch("assistant.Model"),
        patch("assistant.KaldiRecognizer"),
        patch("assistant.SetLogLevel"),
    ):
        from assistant import VoiceAssistant
        assistant = VoiceAssistant(
            mock_config,
            MagicMock(),
            on_event=lambda e, d: events.append((e, d)),
        )
    assistant._events = events
    return assistant


def emitted(va, event_type) -> list[dict]:
    return [d for e, d in va._events if e == event_type]


# --- Wake word handling ---

def test_wake_word_only_emits_wake_word(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus", is_partial=False)
    assert len(emitted(va, AssistantEvent.WAKE_WORD)) == 1
    assert len(emitted(va, AssistantEvent.COMMAND)) == 0


def test_unknown_prefix_does_nothing(va):
    va._handle_vosk_text("computer start", is_partial=False)
    assert va._events == []


def test_wake_word_plus_unknown_command_does_nothing(va):
    va._handle_vosk_text("octopus fly", is_partial=False)
    assert va._events == []


# --- Command dispatch ---

def test_known_command_emits_command_event(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus start", is_partial=False)
    hits = emitted(va, AssistantEvent.COMMAND)
    assert len(hits) == 1
    assert hits[0]["name"] == "start"


def test_command_event_carries_correct_name(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus stop", is_partial=False)
    assert emitted(va, AssistantEvent.COMMAND)[0]["name"] == "stop"


def test_partial_result_triggers_command(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus start", is_partial=True)
    assert len(emitted(va, AssistantEvent.COMMAND)) == 1


# --- Dedup guard ---

def test_dedup_blocks_identical_text_within_window(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus start", is_partial=True)
    va._handle_vosk_text("octopus start", is_partial=False)
    assert len(emitted(va, AssistantEvent.COMMAND)) == 1


def test_dedup_allows_same_text_after_window(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus start", is_partial=False)
    # Expire the dedup window by backdating the timestamp
    va._last_executed_time -= 2.0
    va._handle_vosk_text("octopus start", is_partial=False)
    assert len(emitted(va, AssistantEvent.COMMAND)) == 2


def test_dedup_allows_different_commands(va):
    from assistant import AssistantEvent
    va._handle_vosk_text("octopus start", is_partial=False)
    va._handle_vosk_text("octopus stop", is_partial=False)
    assert len(emitted(va, AssistantEvent.COMMAND)) == 2


# --- _emit robustness ---

def test_emit_swallows_callback_exception(va):
    from assistant import AssistantEvent
    va._on_event = MagicMock(side_effect=RuntimeError("boom"))
    # Should not raise
    va._emit(AssistantEvent.COMMAND, {"name": "start"})


def test_emit_does_nothing_without_callback():
    with (
        patch("assistant.Model"),
        patch("assistant.KaldiRecognizer"),
        patch("assistant.SetLogLevel"),
    ):
        from assistant import VoiceAssistant, AssistantEvent
        cfg = MagicMock()
        cfg.use_porcupine = False
        cfg.wake_word = "octopus"
        cfg.command_names.return_value = []
        cfg.commands = {}
        cfg.vosk_model_path = "vosk-small"
        va = VoiceAssistant(cfg, MagicMock(), on_event=None)
        va._emit(AssistantEvent.WAKE_WORD)  # should not raise


# --- Audio level throttle ---

def test_audio_level_emitted_at_10hz(va):
    from assistant import AssistantEvent
    pcm = np.zeros(512, dtype=np.int16)
    # First call: _last_level_time is 0, so level fires
    va.process_audio(pcm)
    first_count = len(emitted(va, AssistantEvent.AUDIO_LEVEL))
    # Second call immediately: throttled, should NOT fire again
    va.process_audio(pcm)
    assert len(emitted(va, AssistantEvent.AUDIO_LEVEL)) == first_count
    # Backdate to expire throttle window
    va._last_level_time -= 0.2
    va.process_audio(pcm)
    assert len(emitted(va, AssistantEvent.AUDIO_LEVEL)) == first_count + 1


# --- Porcupine mode (wake detector + command recognizer mocked directly) ---

@pytest.fixture
def va_porcupine(va):
    """Attach mock Porcupine components to the Vosk-mode assistant."""
    mock_wwd = MagicMock()
    mock_wwd.frame_length = 512
    mock_wwd.check.return_value = False
    va._wake_detector = mock_wwd

    mock_cr = MagicMock()
    mock_cr.recognize.return_value = None
    va._command_recognizer = mock_cr

    va.audio_processor.process = MagicMock(return_value=np.zeros(512, dtype=np.int16))
    va.audio_processor.process_without_vad = MagicMock(return_value=np.zeros(512, dtype=np.int16))
    return va


def test_process_sleeping_calls_wake_detector(va_porcupine):
    va = va_porcupine
    va._process_sleeping(np.zeros(512, dtype=np.int16))
    va._wake_detector.check.assert_called()


def test_process_sleeping_wake_word_emits_event(va_porcupine):
    from assistant import AssistantEvent
    va = va_porcupine
    va._wake_detector.check.return_value = True
    va._process_sleeping(np.zeros(512, dtype=np.int16))
    assert len(emitted(va, AssistantEvent.WAKE_WORD)) == 1


def test_process_sleeping_transitions_to_listening(va_porcupine):
    from assistant import State
    va = va_porcupine
    va._wake_detector.check.return_value = True
    va._process_sleeping(np.zeros(512, dtype=np.int16))
    assert va.state == State.LISTENING


def test_process_listening_timeout_emits(va_porcupine):
    from assistant import AssistantEvent, State
    va = va_porcupine
    va.state = State.LISTENING
    va._listening_started = time.perf_counter() - va.config.command_timeout - 1
    va._process_listening(np.zeros(512, dtype=np.int16))
    assert len(emitted(va, AssistantEvent.TIMEOUT)) == 1
    assert va.state == State.SLEEPING


def test_process_listening_command_recognized(va_porcupine):
    from assistant import AssistantEvent, State
    va = va_porcupine
    va.state = State.LISTENING
    va._listening_started = time.perf_counter()
    va._command_recognizer.recognize.return_value = "start"
    va.audio_processor.process_without_vad.return_value = np.zeros(3200, dtype=np.int16)
    va._process_listening(np.zeros(3200, dtype=np.int16))
    hits = emitted(va, AssistantEvent.COMMAND)
    assert len(hits) == 1
    assert hits[0]["name"] == "start"


def test_return_to_sleeping_emits_state_change(va_porcupine):
    from assistant import AssistantEvent, State
    va = va_porcupine
    va.state = State.LISTENING
    va._return_to_sleeping()
    assert va.state == State.SLEEPING
    changes = emitted(va, AssistantEvent.STATE_CHANGE)
    assert any(d.get("state") == "sleeping" for d in changes)


def test_cleanup_calls_audio_processor(va_porcupine):
    va = va_porcupine
    va.cleanup()
    va.audio_processor.cleanup.assert_called_once()


def test_process_audio_routes_to_porcupine_sleeping(va_porcupine):
    """process_audio() dispatches to _process_sleeping when use_porcupine=True."""
    va = va_porcupine
    va.config.use_porcupine = True
    va._last_level_time = 0.0  # ensure level fires
    pcm = np.zeros(512, dtype=np.int16)
    va.process_audio(pcm)
    va._wake_detector.check.assert_called()


def test_process_audio_routes_to_porcupine_listening(va_porcupine):
    """process_audio() dispatches to _process_listening when LISTENING state."""
    from assistant import State
    va = va_porcupine
    va.config.use_porcupine = True
    va.state = State.LISTENING
    va._listening_started = time.perf_counter()
    pcm = np.zeros(512, dtype=np.int16)
    # _command_recognizer.recognize returns None → no command, no crash
    va.process_audio(pcm)  # should not raise
