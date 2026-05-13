"""Performance benchmarks: latency, throughput, and memory stability.

Verifies the audio pipeline meets the <500ms end-to-end latency budget.
Requires librnnoise; tests that need it are skipped if unavailable.
"""
import time
import tracemalloc

import numpy as np
import pytest

from rnnoise import rnnoise_available

_CHUNK_SAMPLES = 512
_SAMPLE_RATE = 16000
_CHUNK_DURATION_S = _CHUNK_SAMPLES / _SAMPLE_RATE  # 32 ms per chunk


def _chunks(n: int) -> list[np.ndarray]:
    """Deterministic pseudo-random int16 audio at a speech-like level."""
    rng = np.random.default_rng(42)
    return [rng.integers(-3000, 3000, _CHUNK_SAMPLES, dtype=np.int16) for _ in range(n)]


# ── RNNoise latency ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rnn():
    if not rnnoise_available:
        pytest.skip("librnnoise not installed")
    from rnnoise import RNNoise
    inst = RNNoise()
    yield inst
    inst.close()


def test_rnnoise_latency_under_10ms(rnn):
    """RNNoise per-chunk latency must stay under the 10ms documented budget."""
    from audio_processor import _pcm_to_float
    floats = [_pcm_to_float(c) for c in _chunks(120)]
    for c in floats[:5]:
        rnn.process(c)  # warmup

    t0 = time.perf_counter()
    for c in floats:
        rnn.process(c)
    avg_ms = (time.perf_counter() - t0) * 1000 / len(floats)

    assert avg_ms < 10.0, f"RNNoise avg {avg_ms:.2f}ms/chunk > 10ms budget"


# ── AGC latency ────────────────────────────────────────────────────────────────

def test_agc_latency_under_1ms():
    """AGC per-chunk latency must stay under the 1ms documented budget."""
    from audio_processor import AGC, _pcm_to_float
    agc = AGC()
    floats = [_pcm_to_float(c) for c in _chunks(200)]
    for c in floats[:10]:
        agc.process(c)  # warmup

    t0 = time.perf_counter()
    for c in floats:
        agc.process(c)
    avg_ms = (time.perf_counter() - t0) * 1000 / len(floats)

    assert avg_ms < 1.0, f"AGC avg {avg_ms:.3f}ms/chunk > 1ms budget"


# ── Full pipeline throughput ───────────────────────────────────────────────────

@pytest.mark.skipif(not rnnoise_available, reason="librnnoise not installed")
def test_pipeline_faster_than_realtime():
    """Full AudioProcessor pipeline must run under 0.5× real-time on 100 chunks.

    At 0.5× real-time, 32ms of audio takes <16ms to process, leaving
    headroom for Vosk recognition within the 500ms end-to-end budget.
    """
    from audio_processor import AudioProcessor
    from config import Environment
    chunks = _chunks(100)
    proc = AudioProcessor(Environment.QUIET, enabled=True)
    for c in chunks[:5]:
        proc.process(c)  # warmup

    t0 = time.perf_counter()
    for c in chunks:
        proc.process(c)
    elapsed = time.perf_counter() - t0
    proc.cleanup()

    rt_factor = elapsed / (len(chunks) * _CHUNK_DURATION_S)
    assert rt_factor < 0.5, f"RT factor {rt_factor:.2f} ≥ 0.5 — pipeline can't keep up"


# ── Memory stability ───────────────────────────────────────────────────────────

@pytest.mark.skipif(not rnnoise_available, reason="librnnoise not installed")
def test_pipeline_no_python_memory_growth():
    """Python heap must not grow unboundedly over 500 chunks.

    Catches leaks in numpy array allocation, bytearray growth in the
    vosk buffer, or accumulating residual samples.
    """
    from audio_processor import AudioProcessor
    from config import Environment
    chunks = _chunks(500)
    proc = AudioProcessor(Environment.QUIET, enabled=True)

    for c in chunks[:20]:  # let residual buffer stabilise
        proc.process(c)

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    for c in chunks:
        proc.process(c)

    snap_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    proc.cleanup()

    growth_kb = sum(
        s.size_diff for s in snap_after.compare_to(snap_before, "lineno")
        if s.size_diff > 0
    ) / 1024
    assert growth_kb < 50, f"Python heap grew {growth_kb:.0f} KB over 500 chunks"


def test_rnnoise_residual_stays_bounded(rnn):
    """RNNoise internal residual must never exceed one frame (480 samples)."""
    from audio_processor import _pcm_to_float
    floats = [_pcm_to_float(c) for c in _chunks(200)]
    for c in floats[:10]:
        rnn.process(c)  # stabilise

    max_residual = max(len(rnn._residual) for c in floats for _ in [rnn.process(c)])
    assert max_residual < rnn._frame_size, (
        f"Residual {max_residual} ≥ frame_size {rnn._frame_size}"
    )
