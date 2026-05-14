"""Audio input device selection and PyAudio instance creation."""

import logging
import os
import sys

import pyaudio

logger = logging.getLogger(__name__)


def create_pyaudio() -> pyaudio.PyAudio:
    """Create a PyAudio instance, suppressing ALSA error spam on Linux."""
    stderr_fd = sys.stderr.fileno()
    old_stderr = os.dup(stderr_fd)
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        os.close(devnull)
        pa = pyaudio.PyAudio()
    finally:
        os.dup2(old_stderr, stderr_fd)
        os.close(old_stderr)
    return pa


def get_input_devices(pa: pyaudio.PyAudio) -> list[dict]:
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if int(info["maxInputChannels"]) > 0:
            devices.append(
                {
                    "index": i,
                    "description": info["name"],
                }
            )
    return devices


def _is_loopback(name: str) -> bool:
    return "monitor" in name.lower()


def _prompt_choice(count: int) -> int:
    while True:
        try:
            raw = input(f"\nSelect device [1-{count}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        try:
            choice = int(raw)
        except ValueError:
            print(f"  Invalid input. Enter a number from 1 to {count}.")
            continue

        if choice < 1 or choice > count:
            print(f"  Choice out of range (1-{count}).")
            continue

        return choice


def pick_input_device(pa: pyaudio.PyAudio) -> int:
    """Interactively select an audio input device. Returns PyAudio device index."""
    devices = get_input_devices(pa)
    if not devices:
        print("Error: No audio input devices found.")
        sys.exit(1)

    if len(devices) == 1:
        print(f"Using audio device: {devices[0]['description']}")
        return devices[0]["index"]

    inputs = [d for d in devices if not _is_loopback(d["description"])]
    loopbacks = [d for d in devices if _is_loopback(d["description"])]

    ordered: list[dict] = []
    print("Available input devices:\n")

    if inputs:
        print("  Input Devices:")
        for dev in inputs:
            ordered.append(dev)
            print(f"    [{len(ordered)}] {dev['description']}")

    if loopbacks:
        print("  Loopback / Monitor:")
        for dev in loopbacks:
            ordered.append(dev)
            print(f"    [{len(ordered)}] {dev['description']}")

    choice = _prompt_choice(len(ordered))
    selected = ordered[choice - 1]
    print(f"Using device: {selected['description']}")
    return selected["index"]
