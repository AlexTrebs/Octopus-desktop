"""Shared audio setup/teardown for all CLI modes."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import pyaudio

from audio_devices import create_pyaudio, get_input_devices, pick_input_device
from audio_processor import AudioProcessor, SAMPLE_RATE
from config import Config, CHANNELS, FORMAT, CHUNK_SIZE

logger = logging.getLogger(__name__)


@dataclass
class AudioSession:
    pa: pyaudio.PyAudio
    stream: pyaudio.Stream
    processor: AudioProcessor
    native_rate: int
    read_size: int

    def resample(self, pcm_i16: np.ndarray) -> np.ndarray:
        if self.native_rate == SAMPLE_RATE:
            return pcm_i16
        new_len = int(len(pcm_i16) * SAMPLE_RATE / self.native_rate)
        indices = np.linspace(0, len(pcm_i16) - 1, new_len)
        return np.ascontiguousarray(
            np.interp(indices, np.arange(len(pcm_i16)), pcm_i16.astype(np.float32)).astype(np.int16)
        )


def _find_default_device(pa: pyaudio.PyAudio) -> int | None:
    """Find the 'default' or 'pulse' virtual device index."""
    devices = get_input_devices(pa)
    for preferred in ("default", "pulse", "pipewire"):
        for dev in devices:
            if dev["description"] == preferred:
                return dev["index"]
    return None


def _open_stream(pa, device_index, frames_per_buffer):
    """Open an audio stream with three-step fallback.

    1. Try 16kHz on the requested device
    2. Try the device's native rate (for USB audio interfaces) + resampling
    3. Fall back to 'default' virtual device at 16kHz
    Returns (stream, native_rate, read_size).
    """
    dev_name = pa.get_device_info_by_index(device_index).get("name", str(device_index))

    # Step 1: try 16kHz directly
    try:
        stream = pa.open(
            format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
            input=True, input_device_index=device_index,
            frames_per_buffer=frames_per_buffer,
        )
        logger.info("Audio input: %r @ 16000Hz", dev_name)
        return stream, SAMPLE_RATE, frames_per_buffer
    except Exception as e:
        logger.debug("16kHz stream failed on %r: %s", dev_name, e)

    # Step 2: fall back to default virtual device at 16kHz (avoids native-rate
    # PortAudio/ALSA crashes on PipeWire virtual devices like USB headsets)
    fallback = _find_default_device(pa)
    if fallback is not None and fallback != device_index:
        try:
            fallback_name = pa.get_device_info_by_index(fallback).get("name", str(fallback))
            logger.info("Falling back to %r @ 16000Hz", fallback_name)
            stream = pa.open(
                format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                input=True, input_device_index=fallback,
                frames_per_buffer=frames_per_buffer,
            )
            return stream, SAMPLE_RATE, frames_per_buffer
        except Exception as e:
            logger.debug("Default device fallback failed: %s", e)

    # Step 3: try native rate + resampling as last resort
    try:
        dev_info = pa.get_device_info_by_index(device_index)
        native_rate = int(dev_info["defaultSampleRate"])
        read_size = frames_per_buffer * native_rate // SAMPLE_RATE
        stream = pa.open(
            format=FORMAT, channels=CHANNELS, rate=native_rate,
            input=True, input_device_index=device_index,
            frames_per_buffer=read_size,
        )
        logger.info("Audio input: %r @ %dHz (resampling to 16000Hz)", dev_name, native_rate)
        return stream, native_rate, read_size
    except Exception as e:
        logger.debug("Native rate stream failed on %r: %s", dev_name, e)

    raise RuntimeError("Could not open any audio input device")


@contextmanager
def open_audio_session(
    config: Config,
    frames_per_buffer: int = CHUNK_SIZE,
    device_index: int | None = None,
) -> Generator[AudioSession]:
    processor = AudioProcessor(
        environment=config.environment,
        enabled=config.enable_audio_processing,
    )

    pa = create_pyaudio()
    if device_index is None:
        device_index = pick_input_device(pa)

    stream, native_rate, read_size = _open_stream(pa, device_index, frames_per_buffer)

    try:
        yield AudioSession(pa=pa, stream=stream, processor=processor,
                           native_rate=native_rate, read_size=read_size)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
