"""Test mode — sequential checks for mic, audio pipeline, detection, commands."""

import logging
import time

import numpy as np
from vosk import SetLogLevel

from audio_processor import SAMPLE_RATE
from audio_session import open_audio_session, AudioSession
from config import Config, PROJECT_ROOT, CHUNK_SIZE

logger = logging.getLogger(__name__)


def _test_audio_input(session: AudioSession) -> None:
    print("--- Test 1: Audio Input ---")
    print("Recording 3 seconds of audio to check levels...")
    print("Speak into your microphone:\n")

    levels = []
    for i in range(int(SAMPLE_RATE / CHUNK_SIZE * 3)):
        raw = session.stream.read(session.read_size, exception_on_overflow=False)
        pcm = np.frombuffer(raw, dtype=np.int16)
        rms = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
        db = 20 * np.log10(max(rms, 1) / 32768.0)
        levels.append(db)

        if i % (SAMPLE_RATE // CHUNK_SIZE // 10) == 0:
            bar_len = max(0, int((db + 60) * 0.8))
            bar = "#" * bar_len
            print(f"  Level: {db:6.1f} dB |{bar}")

    avg_level = np.mean(levels)
    max_level = np.max(levels)
    print(f"\n  Average level: {avg_level:.1f} dB")
    print(f"  Peak level:    {max_level:.1f} dB")

    if max_level < -50:
        print("  WARNING: Audio levels very low. Check microphone connection.")
    elif max_level < -30:
        print("  Audio levels OK but quiet. Consider moving closer to mic.")
    else:
        print("  Audio levels good.")


def _test_audio_processing(session: AudioSession) -> None:
    print("\n--- Test 2: Audio Processing Pipeline ---")
    print("Processing 3 seconds of audio through pipeline...")
    print("Speak to test VAD (Voice Activity Detection):\n")

    speech_frames = 0
    total_frames = 0
    for i in range(int(SAMPLE_RATE / CHUNK_SIZE * 3)):
        raw = session.stream.read(session.read_size, exception_on_overflow=False)
        pcm = np.frombuffer(raw, dtype=np.int16)
        pcm = session.resample(pcm)
        total_frames += 1
        result = session.processor.process(pcm)
        if result is not None:
            speech_frames += 1
            if i % (SAMPLE_RATE // CHUNK_SIZE // 5) == 0:
                print("  Speech detected")

    pct = 100 * speech_frames / max(total_frames, 1)
    print(f"\n  Speech frames: {speech_frames}/{total_frames} ({pct:.0f}%)")


def _test_porcupine(session: AudioSession, config: Config) -> None:
    print("\n--- Test 3: Porcupine Wake Word Detection ---")
    if not config.use_porcupine:
        print("  Skipped (no Porcupine .ppn configured, using Vosk wake word mode)")
        return

    try:
        from wake_word_detector import WakeWordDetector

        wake_detector = WakeWordDetector(
            access_key=config.porcupine_access_key,
            model_path=config.porcupine_model_path,
        )
        print(f"  Porcupine initialized (frame size: {wake_detector.frame_length})")
        print(f'  Say "{config.wake_word}" to test detection (10 second window)...\n')

        buffer = np.array([], dtype=np.int16)
        start = time.perf_counter()
        detected = False
        while time.perf_counter() - start < 10:
            raw = session.stream.read(session.read_size, exception_on_overflow=False)
            pcm = np.frombuffer(raw, dtype=np.int16)
            pcm = session.resample(pcm)
            processed = session.processor.process(pcm)
            if processed is not None:
                buffer = np.concatenate([buffer, processed])

            while len(buffer) >= wake_detector.frame_length:
                frame = buffer[: wake_detector.frame_length]
                buffer = buffer[wake_detector.frame_length :]
                if wake_detector.check(frame.tolist()):
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    print(f"  Wake word detected! ({elapsed_ms:.0f}ms into test)")
                    detected = True
                    break
            if detected:
                break

        if not detected:
            print("  No wake word detected in 10 seconds.")
            print("  Tips: speak clearly, closer to mic, check .ppn file path")

        wake_detector.cleanup()

    except RuntimeError as e:
        print(f"  Porcupine error: {e}")


def _test_vosk(session: AudioSession, config: Config) -> None:
    from command_recognizer import CommandRecognizer

    print("\n--- Test 4: Vosk Command Recognition ---")
    SetLogLevel(-1)
    vosk_path = str(PROJECT_ROOT / config.vosk_model_path)
    try:
        recognizer = CommandRecognizer(vosk_path, config.command_names())
        print(f"  Vosk initialized with commands: {config.command_names()}")
        print("  Say a command to test recognition (10 second window)...\n")

        start = time.perf_counter()
        recognized = False
        while time.perf_counter() - start < 10:
            raw = session.stream.read(session.read_size, exception_on_overflow=False)
            pcm = np.frombuffer(raw, dtype=np.int16)
            pcm = session.resample(pcm)
            processed = session.processor.process_without_vad(pcm)

            cmd = recognizer.recognize(processed.tobytes())
            partial = recognizer.get_partial_text()
            if partial:
                logger.debug("Partial: %r", partial)

            if cmd:
                elapsed_ms = (time.perf_counter() - start) * 1000
                print(f"  Recognized: {cmd!r} ({elapsed_ms:.0f}ms)")
                recognized = True
                break

        if not recognized:
            final = recognizer.get_final_text()
            if final:
                print(f"  Final result: {final!r}")
            else:
                print("  No command recognized in 10 seconds.")

    except Exception as e:
        print(f"  Vosk error: {e}")


def _test_command_execution(config: Config) -> None:
    print("\n--- Test 5: Command Execution (dry-run) ---")
    for name, action in config.commands.items():
        print(f"\n  Command: {name!r}")
        action.execute(dry_run=True)


def run_test(config: Config) -> None:
    print("=== TEST MODE ===\n")

    with open_audio_session(config) as session:
        try:
            _test_audio_input(session)
            _test_audio_processing(session)
            _test_porcupine(session, config)
            _test_vosk(session, config)
            _test_command_execution(config)
        finally:
            session.processor.cleanup()

    print("\n=== TEST COMPLETE ===")
