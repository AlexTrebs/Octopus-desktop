"""Vosk-based command recognition with grammar constraints."""

import json

from vosk import KaldiRecognizer, Model


class CommandRecognizer:
    """Recognizes voice commands using a Vosk model restricted to a grammar.

    Checks both partial and final results for lowest latency.
    """

    def __init__(self, model_path: str, command_names: list[str]):
        self.model = Model(model_path)
        self.command_names = command_names
        self._create_recognizer()

    def _create_recognizer(self) -> None:
        grammar = json.dumps(self.command_names + [""])
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetGrammar(grammar)

    def recognize(self, pcm_i16_bytes: bytes) -> str | None:
        """Feed audio and return a command name if recognized, else None."""
        is_final = self.recognizer.AcceptWaveform(pcm_i16_bytes)

        if is_final:
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").strip()
            if text and text in self.command_names:
                return text
        else:
            partial = json.loads(self.recognizer.PartialResult())
            text = partial.get("partial", "").strip()
            if text and text in self.command_names:
                return text

        return None

    def reset(self) -> None:
        self._create_recognizer()

    def get_partial_text(self) -> str:
        partial = json.loads(self.recognizer.PartialResult())
        return partial.get("partial", "")

    def get_final_text(self) -> str:
        result = json.loads(self.recognizer.FinalResult())
        return result.get("text", "")
