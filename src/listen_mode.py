"""Listen mode — transcribes all speech to console without grammar constraints."""

import json
import signal
import threading

import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

import log
from audio_processor import SAMPLE_RATE
from audio_session import open_audio_session
from config import Config, PROJECT_ROOT, CHUNK_SIZE


def run_listen(config: Config) -> None:
    print("=== LISTEN MODE ===")
    print("Transcribing all speech to console. Press Ctrl+C to stop.\n")

    SetLogLevel(-1)
    vosk_path = str(PROJECT_ROOT / config.vosk_model_path)
    model = Model(vosk_path)

    recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    shutdown_event = threading.Event()

    def handle_shutdown(_signum, _frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    with open_audio_session(config, frames_per_buffer=CHUNK_SIZE * 4) as session:
        print(f"{log.timestamp()} Listening...\n")

        last_partial = ""
        try:
            while not shutdown_event.is_set():
                try:
                    raw = session.stream.read(
                        session.read_size, exception_on_overflow=False
                    )
                except IOError:
                    continue

                pcm = np.frombuffer(raw, dtype=np.int16)
                pcm = session.resample(pcm)
                processed = session.processor.process_without_vad(pcm)

                is_final = recognizer.AcceptWaveform(processed.tobytes())

                if is_final:
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        print(f"{log.timestamp()} {text}")
                    last_partial = ""
                else:
                    partial = json.loads(recognizer.PartialResult())
                    text = partial.get("partial", "").strip()
                    if text and text != last_partial:
                        print(
                            f"\r{log.timestamp()} ... {text}", end="", flush=True
                        )
                        last_partial = text

        finally:
            print()
            session.processor.cleanup()
            print("Stopped.")
