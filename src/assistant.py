"""Voice assistant state machine and orchestration.

Vosk mode: single pipeline where Vosk handles wake word + command together.
Porcupine mode: two-stage — Porcupine detects wake word, then Vosk listens
for the command.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from enum import Enum, StrEnum
from typing import TYPE_CHECKING

import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel

from audio_processor import AudioProcessor
from config import Config, PROJECT_ROOT

if TYPE_CHECKING:
    from command_recognizer import CommandRecognizer
    from wake_word_detector import WakeWordDetector

logger = logging.getLogger(__name__)

_DEDUP_WINDOW = 1.0  # seconds — suppresses partial+final firing the same command twice


class AssistantEvent(StrEnum):
    WAKE_WORD = "wake_word"
    COMMAND = "command"
    TIMEOUT = "timeout"
    STATE_CHANGE = "state_change"
    AUDIO_LEVEL = "audio_level"


class State(Enum):
    SLEEPING = "sleeping"
    LISTENING = "listening"


class VoiceAssistant:

    def __init__(
        self,
        config: Config,
        audio_processor: AudioProcessor,
        on_event: Callable[[str, dict], None] | None = None,
    ):
        self.config = config
        self.audio_processor = audio_processor
        self.wake_word = config.wake_word
        self._on_event = on_event
        self._last_level_time = 0.0

        SetLogLevel(-1)

        vosk_path = str(PROJECT_ROOT / config.vosk_model_path)
        self._model = Model(vosk_path)

        # Porcupine mode state
        self._wake_detector: WakeWordDetector | None = None
        self._porcupine_buffer = np.array([], dtype=np.int16)
        self._command_recognizer: CommandRecognizer | None = None

        if config.use_porcupine:
            self._init_porcupine_mode(config, vosk_path)
        else:
            self._init_vosk_mode()

        # In Vosk mode the state machine is unused, but default to SLEEPING
        # so cleanup and debug code has a consistent value.
        self.state = State.SLEEPING
        self._listening_started: float | None = None
        self._wake_word_time: float | None = None
        self._vosk_buffer = bytearray()
        self._vosk_frame_size = 3200  # 200ms at 16kHz

        # Double-fire guard: track last executed text + timestamp to prevent
        # partial + final results executing the same command twice.
        self._last_executed_text: str | None = None
        self._last_executed_time: float = 0.0

        # Rolling pre-buffer of processed audio (Porcupine mode).
        # Keeps ~500ms so Vosk can be seeded on wake word detection.
        self._audio_pre_buffer: deque[np.ndarray] = deque()
        self._pre_buffer_len = 0
        self._pre_buffer_max = 8000  # 500ms at 16kHz

    def _emit(self, event: str, data: dict | None = None) -> None:
        """Fire event callback if set. Never disrupts the audio pipeline."""
        if self._on_event is None:
            return
        try:
            self._on_event(event, data or {})
        except Exception:
            logger.debug("_emit callback error", exc_info=True)

    def _init_porcupine_mode(self, config: Config, vosk_path: str) -> None:
        from wake_word_detector import WakeWordDetector
        from command_recognizer import CommandRecognizer

        self._wake_detector = WakeWordDetector(
            access_key=config.porcupine_access_key,
            model_path=config.porcupine_model_path,
        )
        self._command_recognizer = CommandRecognizer(vosk_path, config.command_names())

    def _init_vosk_mode(self) -> None:
        """Set up single-pipeline Vosk recognition with wake word + command grammar."""
        wake_phrases = [f"{self.wake_word} {cmd}" for cmd in self.config.command_names()]
        wake_phrases.append(self.wake_word)
        grammar = json.dumps(wake_phrases + [""])

        self._recognizer = KaldiRecognizer(self._model, 16000)
        self._recognizer.SetGrammar(grammar)

    def process_audio(self, pcm_i16: np.ndarray) -> None:
        # Throttle audio level events to ~10Hz
        now = time.monotonic()
        if now - self._last_level_time >= 0.1:
            self._last_level_time = now
            level = self.audio_processor.get_audio_level(pcm_i16)
            self._emit(AssistantEvent.AUDIO_LEVEL, {"level": level})

        if self.config.use_porcupine:
            self._process_porcupine(pcm_i16)
        else:
            self._process_vosk_pipeline(pcm_i16)

    def _drain_vosk_frames(self) -> Iterator[bytes]:
        """Yield complete 200ms frames from the buffer, consuming as it goes."""
        frame_bytes = self._vosk_frame_size * 2  # 2 bytes per int16 sample
        while len(self._vosk_buffer) >= frame_bytes:
            chunk = bytes(self._vosk_buffer[:frame_bytes])
            self._vosk_buffer = self._vosk_buffer[frame_bytes:]
            yield chunk

    # -- Vosk single-pipeline mode ------------------------------------------

    def _process_vosk_pipeline(self, pcm_i16: np.ndarray) -> None:
        processed = self.audio_processor.process(pcm_i16)
        if processed is None:
            return

        self._vosk_buffer.extend(processed.tobytes())

        for chunk in self._drain_vosk_frames():
            is_final = self._recognizer.AcceptWaveform(chunk)
            if is_final:
                text = json.loads(self._recognizer.Result()).get("text", "").strip()
                if text:
                    self._handle_vosk_text(text, is_partial=False)
            else:
                text = json.loads(self._recognizer.PartialResult()).get("partial", "").strip()
                if text:
                    self._handle_vosk_text(text, is_partial=True)

    def _handle_vosk_text(self, text: str, is_partial: bool) -> None:
        if not text.startswith(self.wake_word):
            return

        remainder = text[len(self.wake_word):].strip()

        if not remainder:
            logger.debug("Wake word heard, waiting for command...")
            self._emit(AssistantEvent.WAKE_WORD)
            return

        if remainder not in self.config.commands:
            return

        now = time.monotonic()
        if text == self._last_executed_text and (now - self._last_executed_time) < _DEDUP_WINDOW:
            return
        self._last_executed_text = text
        self._last_executed_time = now

        command = self.config.commands[remainder]
        logger.info("Command: %r [%s]", remainder, command.action_type)
        self._emit(AssistantEvent.COMMAND, {"name": remainder})
        threading.Thread(target=command.execute, daemon=True).start()

        self._recognizer.Result()  # flush so next utterance starts clean
        self._vosk_buffer.clear()

    # -- Porcupine two-stage mode -------------------------------------------

    def _process_porcupine(self, pcm_i16: np.ndarray) -> None:
        if self.state == State.SLEEPING:
            self._process_sleeping(pcm_i16)
        elif self.state == State.LISTENING:
            self._process_listening(pcm_i16)

    def _process_sleeping(self, pcm_i16: np.ndarray) -> None:
        if self._wake_detector is None or self._command_recognizer is None:
            return

        processed = self.audio_processor.process(pcm_i16)
        if processed is None:
            return

        # Keep a rolling ~500ms window so Vosk gets seeded the moment the wake word fires
        self._audio_pre_buffer.append(processed.copy())
        self._pre_buffer_len += len(processed)
        while self._pre_buffer_len > self._pre_buffer_max and self._audio_pre_buffer:
            self._pre_buffer_len -= len(self._audio_pre_buffer[0])
            self._audio_pre_buffer.popleft()

        self._porcupine_buffer = np.concatenate([self._porcupine_buffer, processed])

        frame_len = self._wake_detector.frame_length
        while len(self._porcupine_buffer) >= frame_len:
            frame = self._porcupine_buffer[:frame_len]
            self._porcupine_buffer = self._porcupine_buffer[frame_len:]

            if self._wake_detector.check(frame.tolist()):
                self._wake_word_time = time.perf_counter()
                logger.info("Wake word detected — listening for command")
                self._emit(AssistantEvent.WAKE_WORD)
                self.state = State.LISTENING
                self._listening_started = time.perf_counter()

                self._command_recognizer.reset()
                self._vosk_buffer.clear()
                for buffered in self._audio_pre_buffer:
                    self._vosk_buffer.extend(buffered.tobytes())
                self._audio_pre_buffer.clear()
                self._pre_buffer_len = 0
                self._porcupine_buffer = np.array([], dtype=np.int16)
                return

    def _process_listening(self, pcm_i16: np.ndarray) -> None:
        if self._command_recognizer is None:
            return

        if self._listening_started is not None:
            elapsed = time.perf_counter() - self._listening_started
            if elapsed > self.config.command_timeout:
                logger.info("No command heard after %.1fs — returning to sleep", elapsed)
                self._emit(AssistantEvent.TIMEOUT)
                self._return_to_sleeping()
                return

        self._vosk_buffer.extend(self.audio_processor.process_without_vad(pcm_i16).tobytes())

        for chunk in self._drain_vosk_frames():
            command_name = self._command_recognizer.recognize(chunk)
            if command_name is not None:
                latency_ms = (time.perf_counter() - self._wake_word_time) * 1000 if self._wake_word_time else 0
                command = self.config.commands.get(command_name)
                logger.info("Command: %r [%s] %.0fms after wake word", command_name, command.action_type if command else "none", latency_ms)
                self._emit(AssistantEvent.COMMAND, {"name": command_name})
                if command:
                    threading.Thread(target=command.execute, daemon=True).start()
                self._return_to_sleeping()
                return

    def _return_to_sleeping(self) -> None:
        if self._command_recognizer is None:
            return

        self.state = State.SLEEPING
        self._listening_started = None
        self._wake_word_time = None
        self._porcupine_buffer = np.array([], dtype=np.int16)
        self._vosk_buffer.clear()
        self._audio_pre_buffer.clear()
        self._pre_buffer_len = 0
        self._command_recognizer.reset()
        self._emit(AssistantEvent.STATE_CHANGE, {"state": "sleeping"})
        logger.debug("Sleeping — listening for wake word")

    def cleanup(self) -> None:
        if self._wake_detector:
            self._wake_detector.cleanup()
        self.audio_processor.cleanup()
