"""Porcupine-based wake word detection (optional, two-stage mode only)."""

import pvporcupine

from config import PROJECT_ROOT


class WakeWordDetector:
    """Wraps pvporcupine to detect the custom wake word.

    Requires a trained .ppn model file and a valid access key.
    The access key is validated once at startup (requires internet),
    then works fully offline.
    """

    def __init__(self, access_key: str, model_path: str, sensitivity: float = 0.7):
        ppn_path = str(PROJECT_ROOT / model_path)

        try:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[ppn_path],
                sensitivities=[sensitivity],
            )
        except pvporcupine.PorcupineActivationError:
            raise RuntimeError(
                "Porcupine access key validation failed. "
                "Check your PORCUPINE_ACCESS_KEY in config.env. "
                "Get a free key at https://console.picovoice.ai/"
            )
        except pvporcupine.PorcupineActivationLimitError:
            raise RuntimeError(
                "Porcupine access key has reached its activation limit. "
                "Check your account at https://console.picovoice.ai/"
            )
        except pvporcupine.PorcupineActivationRefusedError:
            raise RuntimeError(
                "Porcupine access key was refused. "
                "Check your account at https://console.picovoice.ai/"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Porcupine: {e}")

    @property
    def frame_length(self) -> int:
        return self.porcupine.frame_length

    @property
    def sample_rate(self) -> int:
        return self.porcupine.sample_rate

    def check(self, pcm: list[int]) -> bool:
        keyword_index = self.porcupine.process(pcm)
        return keyword_index >= 0

    def cleanup(self) -> None:
        if hasattr(self, "porcupine") and self.porcupine is not None:
            self.porcupine.delete()
            self.porcupine = None
