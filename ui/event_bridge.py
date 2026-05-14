"""Threading bridge between the audio worker thread and the Qt main thread."""

import logging
import threading

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from audio_session import open_audio_session
from assistant import VoiceAssistant, AssistantEvent
from config import Config, CHUNK_SIZE

logger = logging.getLogger(__name__)


class AssistantSignals(QObject):
    """Pure signal definitions for thread-safe event delivery."""

    wake_word_detected = pyqtSignal()
    command_recognized = pyqtSignal(str)
    command_timeout = pyqtSignal()
    state_changed = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()


class AudioWorkerThread(QThread):
    """Runs the audio capture and voice assistant loop in a background thread."""

    def __init__(
        self,
        config: Config,
        device_index: int | None,
        signals: AssistantSignals,
    ):
        super().__init__()
        self._config = config
        self._device_index = device_index
        self._signals = signals
        self._stop_event = threading.Event()

    def _on_event(self, event: str, data: dict) -> None:
        if event == AssistantEvent.WAKE_WORD:
            self._signals.wake_word_detected.emit()
        elif event == AssistantEvent.COMMAND:
            self._signals.command_recognized.emit(data.get("name", ""))
        elif event == AssistantEvent.TIMEOUT:
            self._signals.command_timeout.emit()
        elif event == AssistantEvent.STATE_CHANGE:
            self._signals.state_changed.emit(data.get("state", ""))
        elif event == AssistantEvent.AUDIO_LEVEL:
            self._signals.audio_level.emit(data.get("level", -100.0))

    def run(self) -> None:
        try:
            with open_audio_session(
                self._config,
                device_index=self._device_index,
            ) as session:
                assistant = VoiceAssistant(
                    self._config,
                    session.processor,
                    on_event=self._on_event,
                )
                self._signals.started.emit()
                logger.info("Audio worker started")

                while not self._stop_event.is_set():
                    try:
                        raw = session.stream.read(
                            session.read_size, exception_on_overflow=False
                        )
                    except IOError as e:
                        logger.debug("Audio read error: %s", e)
                        continue

                    pcm = np.frombuffer(raw, dtype=np.int16)
                    pcm = session.resample(pcm)
                    assistant.process_audio(pcm)

                assistant.cleanup()
        except Exception as e:
            logger.error("Audio worker error: %s", e)
            self._signals.error_occurred.emit(str(e))
        finally:
            self._signals.stopped.emit()
            logger.info("Audio worker stopped")

    def request_stop(self) -> None:
        """Signal the audio loop to exit cleanly."""
        self._stop_event.set()
