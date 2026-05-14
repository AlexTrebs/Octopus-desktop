# Octopus Voice Assistant

A low-latency, offline voice assistant for controlling recording equipment during live performances. Uses Vosk for speech recognition with optional Porcupine wake word detection.

## How It Works

**Vosk mode (default):** Vosk continuously listens for "octopus" + command in a single pass (e.g. "octopus start"). No extra setup needed.

**Porcupine mode (optional):** Porcupine detects the wake word, then Vosk listens for the command separately. Requires a Picovoice access key and custom `.ppn` model file. Enabled automatically when `PORCUPINE_ACCESS_KEY` is set in `config.env` and a valid `.ppn` file exists.

In both modes:
1. Recognizes commands using Vosk with grammar constraints
2. Executes the command (keyboard shortcut, DAW control, etc.)
3. Returns to listening for the wake word

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PortAudio (for PyAudio)
- A microphone
- Optional: `librnnoise` for neural noise suppression (falls back to spectral subtraction)

### System Dependencies (Linux)

```bash
sudo apt install portaudio19-dev python3-dev
# Optional: neural noise suppression
sudo apt install librnnoise0
```

### System Dependencies (macOS)

```bash
brew install portaudio
# Optional: neural noise suppression
brew install rnnoise
```

### Setup

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or without uv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Porcupine Access Key (optional)

Only needed if you want two-stage wake word detection instead of the default Vosk mode.

1. Create a free account at https://console.picovoice.ai/
2. Get your Access Key from the dashboard
3. Add it to `config.env` as `PORCUPINE_ACCESS_KEY`
4. Install: `uv pip install pvporcupine`

Note: Porcupine needs internet **once at startup** to validate the access key, then works fully offline.

### Custom Wake Word Model (Porcupine mode only)

1. Go to https://console.picovoice.ai/
2. Navigate to Porcupine > Custom Keywords
3. Record "octopus" 3 times when prompted
4. Download the `.ppn` file for your platform (Linux/macOS/Windows)
5. Place it in the project root and update `PORCUPINE_MODEL_PATH` in `config.env`

### Vosk Model

Download the small English (GB) model:

```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-gb-0.15.tar.gz
tar xzf vosk-model-small-en-gb-0.15.tar.gz
rm vosk-model-small-en-gb-0.15.tar.gz
```

Other models are available at https://alphacephei.com/vosk/models

## Configuration

Edit `config.env` with your settings:

### config.env Options

| Setting | Default | Description |
|---------|---------|-------------|
| `PORCUPINE_ACCESS_KEY` | (empty) | Your Picovoice access key (optional, enables Porcupine mode) |
| `PORCUPINE_MODEL_PATH` | `octopus_custom.ppn` | Path to custom wake word model |
| `VOSK_MODEL_PATH` | `vosk-model-small-en-gb-0.15` | Path to Vosk model directory |
| `WAKE_WORD` | `octopus` | Wake word (for display only) |
| `ENVIRONMENT` | `Moderate` | `Quiet`, `Moderate`, or `Loud` |
| `COMMAND_TIMEOUT` | `3` | Seconds to wait for command |
| `ENABLE_AUDIO_PROCESSING` | `true` | Enable AGC + noise reduction + VAD |
| `DEBUG` | `false` | Verbose debug output |

### Environment Modes

- **Quiet**: Least aggressive VAD. Best for home studios and quiet rooms.
- **Moderate**: Balanced. Good for rehearsal spaces.
- **Loud**: Most aggressive VAD. For live stages with high ambient noise.

For best accuracy in loud environments, use a headset microphone close to your mouth.

## Usage

### Normal Operation

```bash
uv run src/main.py
```

Say "octopus start" (Vosk mode) or "octopus" then "start" (Porcupine mode).

### Test Mode

```bash
uv run src/main.py --test
```

Runs through a series of tests:
1. Microphone audio levels
2. Audio processing pipeline (VAD detection)
3. Porcupine wake word detection
4. Vosk command recognition
5. Command execution dry-run (prints without pressing keys)

### Listen Mode

```bash
uv run src/main.py --listen
```

Transcribes all speech to the console without grammar constraints. Useful for:
- Verifying your microphone works
- Seeing what Vosk hears
- Debugging recognition issues
- Testing in different environments

## Commands

Commands are defined in `commands.json`. Three action types are supported:

### Keyboard Actions

Simulate key presses. Each command has a `keys` field: a list of chords executed in sequence.

```json
{
  "save": {
    "action": "keyboard",
    "keys": [["Control", "s"]]
  }
}
```

**Chord format**: Each inner list is a set of keys pressed simultaneously. Multiple chords are executed in sequence with 50ms delay.

```json
{
  "copy and paste": {
    "action": "keyboard",
    "keys": [["Control", "c"], ["Control", "v"]]
  }
}
```

**Repeat keys**: Press the same key multiple times by listing it as separate single-key chords.

```json
{
  "up": {
    "action": "keyboard",
    "keys": [["VolumeUp"], ["VolumeUp"], ["VolumeUp"]]
  }
}
```

**Supported key names**:

| Category | Keys |
|----------|------|
| Media | `MediaPlayPause`, `MediaStop`, `MediaNextTrack`, `MediaPreviousTrack` |
| Volume | `VolumeUp`, `VolumeDown`, `VolumeMute` |
| Modifiers | `Control`, `Shift`, `Alt`, `Command` (macOS), `Windows` (Windows) |
| Function | `F1` through `F12` |
| Navigation | `Up`, `Down`, `Left`, `Right`, `Home`, `End`, `PageUp`, `PageDown` |
| Special | `Escape`, `Tab`, `Space`, `Return`, `Backspace`, `Delete` |
| Characters | Any single lowercase letter: `a`, `b`, `c`, etc. |

### DAW Actions (Placeholder)

For future DAW integration via MIDI/OSC. Currently prints what would be done.

```json
{
  "record drums": {
    "action": "daw",
    "track": "drums",
    "command": "record"
  }
}
```

DAW commands: `record`, `stop`, `play`, `mute`, `solo`, `loop_enable`, `loop_disable`

### None Actions

Acknowledge the command without doing anything.

```json
{
  "cancel": {
    "action": "none"
  }
}
```

## Architecture

```
main.py                 Entry point, argument parsing, normal mode audio loop
config.py               Configuration loading and validation
rnnoise.py              RNNoise ctypes wrapper (system librnnoise)
audio_processor.py      Spectral denoise fallback, AGC, VAD pipeline
audio_session.py        Shared audio setup/teardown context manager
audio_devices.py        Audio device selection (pactl / PyAudio)
wake_word_detector.py   Porcupine wrapper (optional)
command_recognizer.py   Vosk wrapper with grammar constraints
command_executor.py     Keyboard simulation, DAW placeholders
assistant.py            State machine orchestration
test_mode.py            --test mode (mic, pipeline, detection, dry-run)
listen_mode.py          --listen mode (transcribe all speech)
log.py                  Logging setup and timestamp helper
```

### Audio Pipeline

```
Microphone (16kHz mono) -> Noise Suppression (RNNoise/spectral) -> AGC -> VAD -> Porcupine/Vosk
```

### State Machine

```
SLEEPING  --[wake word]--> LISTENING
LISTENING --[command]----> SLEEPING
LISTENING --[timeout]----> SLEEPING
```

## Performance

### Typical Latency

**Vosk mode (default):**

| Stage | Time |
|-------|------|
| Audio processing | ~12ms |
| Vosk wake word + command | 370-480ms |
| **Total** | **~370-480ms** |

**Porcupine mode:**

| Stage | Time |
|-------|------|
| Porcupine wake word | 50-80ms |
| Audio processing | ~12ms |
| Vosk command recognition | 100-170ms |
| **Total** | **~160-250ms** |

### Resource Usage

- CPU: 5-8% continuous (single core)
- Memory: ~120 MB (mostly Vosk model)
- Disk: ~200 MB (models + dependencies)

## Troubleshooting

### "No module named 'pyaudio'"
Install PortAudio system library first (`sudo apt install portaudio19-dev`), then `uv pip install PyAudio`.

### "Porcupine access key validation failed"
Check your `PORCUPINE_ACCESS_KEY` in `config.env`. Porcupine needs internet once at startup to validate.

### "Vosk model not found"
Download the model (see Installation section above).

### Wake word not detected
- Try `uv run src/main.py --test` to check audio levels
- Move closer to the microphone
- Try `ENVIRONMENT=Quiet` for less aggressive VAD
- Ensure `.ppn` file matches your platform (Linux/macOS/Windows)

### Commands not recognized
- Use `uv run src/main.py --listen` to see what Vosk hears
- Keep commands short (single words work best)
- Speak clearly after the wake word
- Increase `COMMAND_TIMEOUT` if you need more time

### Audio glitches or high latency
- Close other audio applications
- Try a different microphone
- Set `ENABLE_AUDIO_PROCESSING=false` to bypass the processing pipeline

### Keyboard shortcuts not working
- On Linux, pynput requires X11 or Wayland with appropriate permissions
- On Wayland, you may need to run under X11 compatibility or use xdotool
- Run from a terminal within the desktop session (not SSH)
