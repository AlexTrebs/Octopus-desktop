"""Audio processing pipeline: RNNoise -> AGC -> VAD."""

import logging

import numpy as np
import webrtcvad

from config import Environment
from rnnoise import RNNoise

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def _pcm_to_float(pcm_i16: np.ndarray) -> np.ndarray:
    return pcm_i16.astype(np.float32) / 32768.0


def _float_to_pcm(audio_f32: np.ndarray) -> np.ndarray:
    return (audio_f32 * 32768.0).astype(np.int16)


class AGC:
    """Automatic Gain Control with smooth attack/release."""

    def __init__(self, target_db: float = -20.0, max_gain: float = 10.0):
        self.target_level = 10 ** (target_db / 20.0)
        self.current_gain = 1.0
        self.max_gain = max_gain
        self.attack_coeff = 1.0 - np.exp(-1.0 / (SAMPLE_RATE * 0.05))
        self.release_coeff = 1.0 - np.exp(-1.0 / (SAMPLE_RATE * 0.2))

    def process(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio

        rms = np.sqrt(np.mean(audio**2))
        if rms < 1e-10:
            return audio

        desired_gain = min(self.target_level / rms, self.max_gain)

        if desired_gain > self.current_gain:
            coeff = self.attack_coeff
        else:
            coeff = self.release_coeff

        self.current_gain += coeff * (desired_gain - self.current_gain)

        result = audio * self.current_gain
        return np.clip(result, -1.0, 1.0)


class AudioProcessor:
    """Complete audio processing pipeline: Noise Suppression -> AGC -> VAD.

    Operates on 16kHz mono 16-bit PCM input. Uses RNNoise when the system
    librnnoise is available.
    """

    def __init__(self, environment: Environment, enabled: bool = True):
        self.enabled = enabled
        self._vad_error_count = 0
        self.agc = AGC(target_db=-20.0, max_gain=10.0)

        self.denoiser: RNNoise | None = None
        if enabled:
            try:
                self.denoiser = RNNoise()
            except RuntimeError:
                logger.warning("RNNoise unavailable — running without noise suppression")

        self.vad = webrtcvad.Vad()
        if environment == Environment.QUIET:
            self.vad.set_mode(0)
        elif environment == Environment.MODERATE:
            self.vad.set_mode(1)
        else:
            self.vad.set_mode(3)

    def process(self, pcm_i16: np.ndarray) -> np.ndarray | None:
        """Run full pipeline. Returns processed samples, or None if VAD rejects."""
        if not self.enabled:
            return pcm_i16

        audio_f32 = _pcm_to_float(pcm_i16)
        if self.denoiser is not None:
            audio_f32 = self.denoiser.process(audio_f32)
            if len(audio_f32) == 0:
                return None

        audio_f32 = self.agc.process(audio_f32)
        processed_i16 = _float_to_pcm(audio_f32)

        if not self._check_vad(processed_i16):
            return None

        return processed_i16

    def process_without_vad(self, pcm_i16: np.ndarray) -> np.ndarray:
        """Run noise suppression and AGC only, skip VAD."""
        if not self.enabled:
            return pcm_i16

        audio_f32 = _pcm_to_float(pcm_i16)
        if self.denoiser is not None:
            audio_f32 = self.denoiser.process(audio_f32)
            if len(audio_f32) == 0:
                return pcm_i16
        audio_f32 = self.agc.process(audio_f32)
        return _float_to_pcm(audio_f32)

    def _check_vad(self, pcm_i16: np.ndarray) -> bool:
        """Check if audio chunk contains speech using WebRTC VAD."""
        frame_size = 320  # 20ms at 16kHz
        pcm_bytes = pcm_i16.tobytes()

        # Split audio into 20ms frames for VAD. Return True on first speech frame.
        for i in range(0, len(pcm_bytes) - frame_size * 2 + 1, frame_size * 2):
            frame = pcm_bytes[i : i + frame_size * 2]
            try:
                if self.vad.is_speech(frame, SAMPLE_RATE):
                    return True
            except Exception as e:
                self._vad_error_count += 1
                if self._vad_error_count == 1 or self._vad_error_count % 100 == 0:
                    logger.warning("VAD error #%d: %s", self._vad_error_count, e)

        return False

    def cleanup(self) -> None:
        if self.denoiser is not None:
            self.denoiser.close()

    def get_audio_level(self, pcm_i16: np.ndarray) -> float:
        """Calculate RMS level in dB for debug output."""
        if len(pcm_i16) == 0:
            return -100.0
        rms = np.sqrt(np.mean(pcm_i16.astype(np.float32) ** 2))
        if rms < 1:
            return -100.0
        return 20 * np.log10(rms / 32768.0)
