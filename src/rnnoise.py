"""RNNoise neural noise suppression via system librnnoise (ctypes wrapper).

Handles upsampling 16kHz->48kHz, RNNoise processing, and downsampling back.
"""

import ctypes
import ctypes.util

import numpy as np

_RNNOISE_RATE = 48000
_PIPELINE_RATE = 16000
_RESAMPLE_FACTOR = _RNNOISE_RATE // _PIPELINE_RATE  # 3


def _setup_rnnoise_bindings(lib):
    lib.rnnoise_get_frame_size.restype = ctypes.c_int
    lib.rnnoise_get_frame_size.argtypes = []
    lib.rnnoise_create.restype = ctypes.c_void_p
    lib.rnnoise_create.argtypes = [ctypes.c_void_p]
    lib.rnnoise_destroy.restype = None
    lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
    lib.rnnoise_process_frame.restype = ctypes.c_float
    lib.rnnoise_process_frame.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
    ]


def _load_rnnoise():
    """Try to load librnnoise shared library. Returns None if unavailable."""
    candidates = ["librnnoise.so", "librnnoise.dylib", "rnnoise.dll", "rnnoise"]
    for name in candidates:
        try:
            lib = ctypes.cdll.LoadLibrary(name)
            _setup_rnnoise_bindings(lib)
            return lib
        except OSError:
            continue

    path = ctypes.util.find_library("rnnoise")
    if path:
        try:
            lib = ctypes.cdll.LoadLibrary(path)
            _setup_rnnoise_bindings(lib)
            return lib
        except OSError:
            pass

    return None


_rnnoise_lib = _load_rnnoise()

rnnoise_available: bool = _rnnoise_lib is not None


class RNNoise:
    """RNNoise denoiser operating on 16kHz float32 audio.

    Upsamples to 48kHz for RNNoise processing and downsamples back.
    Use as a context manager or call close() explicitly.
    """

    def __init__(self):
        if _rnnoise_lib is None:
            raise RuntimeError(
                "librnnoise not found. Install it with your package manager "
                "(e.g. pacman -S rnnoise, apt install librnnoise0)."
            )
        self._lib = _rnnoise_lib
        self._state = self._lib.rnnoise_create(ctypes.c_void_p(0))
        self._frame_size = self._lib.rnnoise_get_frame_size()  # 480 at 48kHz
        # Pre-allocate frame buffers to avoid per-call allocation
        self._in_frame = np.empty(self._frame_size, dtype=np.float32)
        self._out_frame = np.empty(self._frame_size, dtype=np.float32)
        self._in_ptr = self._in_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self._out_ptr = self._out_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self._residual = np.empty(0, dtype=np.float32)

    def process(self, audio_f32: np.ndarray) -> np.ndarray:
        """Process 16kHz float32 audio through RNNoise. Returns denoised 16kHz."""
        if len(audio_f32) == 0:
            return audio_f32

        # Upsample 16kHz -> 48kHz via linear interpolation
        n_in = len(audio_f32)
        x_in = np.arange(n_in)
        x_out = np.arange(n_in * _RESAMPLE_FACTOR) / _RESAMPLE_FACTOR
        upsampled = np.interp(x_out, x_in, audio_f32).astype(np.float32)

        # RNNoise expects int16-range floats
        scaled = upsampled * 32768.0

        # Prepend leftover samples from last call
        if len(self._residual) > 0:
            scaled = np.concatenate([self._residual, scaled])
            self._residual = np.empty(0, dtype=np.float32)

        # Process complete frames
        n_frames = len(scaled) // self._frame_size
        if n_frames == 0:
            self._residual = scaled
            return np.empty(0, dtype=np.float32)

        usable = n_frames * self._frame_size
        leftover = len(scaled) - usable
        if leftover > 0:
            self._residual = scaled[usable:].copy()

        denoised_48k = np.empty(usable, dtype=np.float32)
        for i in range(n_frames):
            offset = i * self._frame_size
            np.copyto(self._in_frame, scaled[offset:offset + self._frame_size])
            self._lib.rnnoise_process_frame(self._state, self._out_ptr, self._in_ptr)
            denoised_48k[offset:offset + self._frame_size] = self._out_frame

        denoised_48k /= 32768.0

        # Downsample 48kHz -> 16kHz by averaging groups of 3
        n_out = len(denoised_48k) // _RESAMPLE_FACTOR
        denoised_16k = denoised_48k[:n_out * _RESAMPLE_FACTOR].reshape(-1, _RESAMPLE_FACTOR).mean(axis=1)

        return np.clip(denoised_16k, -1.0, 1.0).astype(np.float32)

    def close(self) -> None:
        """Release the RNNoise C state. Safe to call multiple times."""
        if self._state is not None:
            self._lib.rnnoise_destroy(self._state)
            self._state = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
