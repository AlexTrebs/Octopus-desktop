"""Tests for the audio processing pipeline: AGC, VAD, and AudioProcessor."""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# --- AGC (no mocking needed — pure numpy) ---

def make_agc():
    from audio_processor import AGC
    return AGC(target_db=-20.0, max_gain=10.0)


def test_agc_empty_input():
    agc = make_agc()
    empty = np.array([], dtype=np.float32)
    result = agc.process(empty)
    assert len(result) == 0


def test_agc_silence_passthrough():
    agc = make_agc()
    silence = np.zeros(1600, dtype=np.float32)
    result = agc.process(silence)
    # rms < 1e-10 → returns input unchanged
    assert np.array_equal(result, silence)


def test_agc_amplifies_quiet_signal():
    agc = make_agc()
    quiet = np.full(1600, 0.001, dtype=np.float32)
    result = agc.process(quiet)
    # Should be louder than input
    assert np.mean(np.abs(result)) > np.mean(np.abs(quiet))


def test_agc_clips_at_one():
    agc = make_agc()
    loud = np.full(1600, 2.0, dtype=np.float32)
    result = agc.process(loud)
    assert np.all(result <= 1.0)
    assert np.all(result >= -1.0)


def test_agc_reduces_loud_signal():
    agc = make_agc()
    # Very loud signal: rms ~ 0.9, target ~ -20dB ~ 0.1
    loud = np.full(1600, 0.9, dtype=np.float32)
    result = agc.process(loud)
    assert np.mean(np.abs(result)) < np.mean(np.abs(loud))


# --- get_audio_level ---

@pytest.fixture
def processor_passthrough():
    """AudioProcessor with RNNoise mocked as a passthrough."""
    with patch("audio_processor.RNNoise") as MockRNNoise:
        instance = MagicMock()
        instance.process.side_effect = lambda x: x
        MockRNNoise.return_value = instance
        from audio_processor import AudioProcessor
        from config import Environment
        yield AudioProcessor(Environment.MODERATE, enabled=True)


def test_get_audio_level_silence(processor_passthrough):
    silence = np.zeros(512, dtype=np.int16)
    assert processor_passthrough.get_audio_level(silence) == -100.0


def test_get_audio_level_empty(processor_passthrough):
    assert processor_passthrough.get_audio_level(np.array([], dtype=np.int16)) == -100.0


def test_get_audio_level_full_scale(processor_passthrough):
    # Full-scale sine: 32767 peak → rms ~23170 → ~-3 dB FS
    t = np.linspace(0, 1, 1600)
    signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    level = processor_passthrough.get_audio_level(signal)
    assert -10 < level < 0


def test_get_audio_level_quarter_scale(processor_passthrough):
    t = np.linspace(0, 1, 1600)
    signal = (np.sin(2 * np.pi * 440 * t) * 8192).astype(np.int16)
    level = processor_passthrough.get_audio_level(signal)
    full_scale_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    full_scale_level = processor_passthrough.get_audio_level(full_scale_signal)
    # Quarter scale should be ~12 dB quieter
    assert level < full_scale_level - 10


# --- AudioProcessor pipeline ---

def test_process_disabled_is_passthrough():
    with patch("audio_processor.RNNoise") as MockRNNoise:
        MockRNNoise.return_value = MagicMock()
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=False)

    pcm = np.ones(512, dtype=np.int16)
    result = proc.process(pcm)
    assert np.array_equal(result, pcm)


def test_process_without_vad_disabled_is_passthrough():
    with patch("audio_processor.RNNoise") as MockRNNoise:
        MockRNNoise.return_value = MagicMock()
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=False)

    pcm = np.ones(512, dtype=np.int16)
    result = proc.process_without_vad(pcm)
    assert np.array_equal(result, pcm)


def test_process_returns_none_when_rnnoise_returns_empty():
    with patch("audio_processor.RNNoise") as MockRNNoise:
        instance = MagicMock()
        instance.process.return_value = np.array([], dtype=np.float32)
        MockRNNoise.return_value = instance
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=True)

    pcm = np.ones(512, dtype=np.int16)
    assert proc.process(pcm) is None


def test_process_returns_none_when_vad_rejects(processor_passthrough):
    # Silence is rejected by VAD (no speech frames)
    silence = np.zeros(3200, dtype=np.int16)
    result = processor_passthrough.process(silence)
    assert result is None


def test_process_without_vad_returns_array(processor_passthrough):
    pcm = np.ones(512, dtype=np.int16)
    result = processor_passthrough.process_without_vad(pcm)
    assert isinstance(result, np.ndarray)
    assert len(result) > 0


def test_vad_error_count_increments(processor_passthrough):
    # Force VAD to raise by passing a frame of wrong size
    proc = processor_passthrough
    with patch.object(proc.vad, "is_speech", side_effect=Exception("bad frame")):
        pcm = np.ones(3200, dtype=np.int16)
        proc._check_vad(pcm)
    assert proc._vad_error_count > 0


def test_pcm_float_roundtrip():
    from audio_processor import _pcm_to_float, _float_to_pcm
    original = np.array([0, 1000, -1000, 32767, -32768], dtype=np.int16)
    roundtrip = _float_to_pcm(_pcm_to_float(original))
    # Allow ±1 LSB rounding error
    assert np.all(np.abs(roundtrip.astype(np.int32) - original.astype(np.int32)) <= 1)


# --- RNNoise guarded construction ---

def test_processor_disabled_skips_rnnoise():
    """AudioProcessor(enabled=False) must not instantiate RNNoise."""
    with patch("audio_processor.RNNoise") as MockRNNoise:
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=False)
    MockRNNoise.assert_not_called()
    assert proc.denoiser is None


def test_processor_enabled_with_rnnoise_unavailable_still_constructs():
    """If RNNoise raises RuntimeError (librnnoise absent), processor still works."""
    with patch("audio_processor.RNNoise", side_effect=RuntimeError("no lib")):
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=True)
    assert proc.denoiser is None
    # process() must still function — falls through AGC+VAD without denoiser
    pcm = np.ones(512, dtype=np.int16)
    # result is None (VAD rejects silence) or ndarray — just must not raise
    proc.process(pcm)


def test_cleanup_with_no_denoiser_is_safe():
    """cleanup() must not raise when denoiser is None."""
    with patch("audio_processor.RNNoise") as MockRNNoise:
        from audio_processor import AudioProcessor
        from config import Environment
        proc = AudioProcessor(Environment.MODERATE, enabled=False)
    proc.cleanup()  # denoiser is None — must not raise
