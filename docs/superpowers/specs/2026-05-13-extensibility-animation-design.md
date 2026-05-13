# Octopus — Extensibility & Animation Design

**Date:** 2026-05-13
**Status:** Approved

---

## Goal

Make the assistant easy to extend with new action types (MIDI, OSC, HTTP, OBS, etc.) without touching core files, and add per-command GIF animations that users can supply themselves. Keep keyboard shortcuts as the MVP action type. Keep the existing QPainter octopus for state animations; add GIF playback as an optional overlay.

---

## 1. Action Plugin System

### Problem

Adding a new action type today requires editing three files: `config.py` (new dataclass), `command_executor.py` (new dispatch case), and the `Command` union type. There is no convention for external contributors.

### Solution

Each action type becomes a self-contained Python file in `src/actions/`. A registry in `src/actions/__init__.py` auto-discovers them at startup by scanning the folder. `commands.json` syntax is unchanged — `"action": "keyboard"` resolves to `src/actions/keyboard.py`. An external contributor drops a file in the folder and declares its type name in their commands file. No core edits required.

### Directory layout

```
src/actions/
  __init__.py     # registry: scan, register, build(name, data) → Action
  base.py         # Action ABC
  keyboard.py     # KeyboardAction (moved from config.py)
  daw.py          # DawAction stub (moved from config.py)
  none.py         # NoneAction (moved from config.py)
```

### Action base class (`src/actions/base.py`)

```python
class Action(ABC):
    action_type: ClassVar[str]          # e.g. "keyboard" — used for registry lookup
    name: str                           # command name, e.g. "start recording"
    animation: str | None = None        # optional GIF stem, e.g. "start_recording"

    @abstractmethod
    def execute(self, dry_run: bool = False) -> None: ...

    @classmethod
    @abstractmethod
    def from_config(cls, name: str, data: dict) -> "Action": ...
```

Each concrete class sets `action_type = "keyboard"` (or `"daw"`, `"none"`, etc.) as a class variable. The registry uses this to map config strings to classes. `from_config()` is responsible for reading the optional `"animation"` key from `data` and setting `self.animation`. `AnimationController` reads `action.animation` directly — `Config` does not need to track animations separately.

### Registry (`src/actions/__init__.py`)

Three public functions:

- `load_all()` — scans `src/actions/` for `.py` files (excluding `base.py` and `__init__.py`), imports each, expects them to call `register(MyAction)` at module level.
- `register(action_class)` — adds the class to the `_REGISTRY` dict keyed by `action_type`.
- `build(name: str, data: dict) -> Action` — looks up `data["action"]` in the registry, calls `from_config(name, data)`, raises `ConfigError` on unknown type.

### Config changes

`config.py` loses `KeyboardAction`, `DawAction`, `NoneAction`, and the `Command` union. `_load_commands` calls `actions.build(name, data)` and stores `dict[str, Action]`. Key validation in `validate()` moves into `KeyboardAction.from_config()` — it raises `ConfigError` directly on invalid key names so the error is owned by the action class.

### `command_executor.py`

`parse_key` and `_KEY_MAP` move into `keyboard.py`. The remaining `execute()` dispatch function in `command_executor.py` is replaced in `assistant.py` with a direct call to `action.execute()`. `command_executor.py` is then deleted.

---

## 2. Animation System

### Two layers

| Layer | Driven by | Format | Always on? |
|---|---|---|---|
| State animation | Assistant state (idle / listening / processing) | QPainter code | Yes |
| Command animation | Specific command fired | GIF file | Optional, per-command |

The two layers are independent. State animation always runs. A command animation temporarily replaces QPainter output for its duration, then hands back to the state animation.

### Declaring a command animation

`commands.json` gains an optional `animation` field:

```json
{
  "start recording": {
    "action": "keyboard",
    "keys": [["F5"]],
    "animation": "start_recording"
  }
}
```

The value is a filename stem. The file is resolved as `assets/animations/<stem>.gif`. If the field is absent or the file does not exist, the octopus falls back to the existing "processing" state transition — no error, no crash.

### Assets folder

```
assets/
  animations/
    example.gif     # bundled example
```

`Config` stores the `animation` stem alongside the action. It does not validate that the file exists at startup — a missing GIF is a silent fallback, not a fatal error, so a user can ship a config before they have finished drawing all their animations.

### `AnimationController` (`ui/animation_controller.py`)

New component. Owns the mapping from command name → `QMovie`. `MainWindow` constructs it and passes in the config and the octopus widget.

Responsibilities:
- Receives `command_recognized(name: str)` signal.
- Looks up `config.commands[name].animation` (may be `None`).
- If an animation is configured and the GIF file exists: loads via `QMovie`, calls `octopus.play_animation(movie)`.
- If no animation or file missing: calls `octopus.set_state("processing")` and schedules a 1.2s return to idle via `QTimer` — identical to current behaviour.
- Connects `OctopusWidget.animation_finished` signal to reset state to idle after playback.

GIF files are loaded lazily on first use and cached in a `dict[str, QMovie]` for the session.

### `OctopusWidget` changes

Two additions only — everything else is untouched:

1. `set_audio_level(db: float)` — called at ~10Hz from `_on_audio_level`. Maps dB to a `_live_amplitude` float. `_tick()` uses this to modulate tentacle wave amplitude, making tentacles react to mic volume in real time.

2. `play_animation(movie: QMovie)` — stores the `QMovie`, connects its `frameChanged` signal to `update()` and its `finished` signal to `animation_finished`. `paintEvent` renders `movie.currentPixmap()` instead of QPainter drawing while a movie is active. On `finished`, the movie reference is cleared and QPainter resumes.

New signal: `animation_finished = pyqtSignal()`.

### `MainWindow` changes

`_on_command` delegates to `AnimationController`:

```python
def _on_command(self, name: str) -> None:
    self._status_label.setText(f"Command: {name}")
    self._animation_controller.on_command(name)
```

`_on_audio_level` gains one line:

```python
def _on_audio_level(self, level: float) -> None:
    self._level_meter.set_level(level)
    self._octopus.set_audio_level(level)
```

---

## 3. Data Flow

```
Microphone
  → AudioWorkerThread (QThread)
    → VoiceAssistant.process_audio()
      → action.execute() in daemon thread
      → AssistantEvent.COMMAND → _on_event callback
        → AssistantSignals.command_recognized.emit(name)   ← thread boundary
          → AnimationController.on_command(name)            ← Qt main thread
            → OctopusWidget.play_animation(movie) or set_state("processing")
          → MainWindow._on_command(name)
            → status label update
```

The thread boundary is unchanged. `AssistantSignals` is the only crossing point.

### Component ownership

| Component | Owns | Talks to |
|---|---|---|
| `AudioWorkerThread` | audio loop, `VoiceAssistant` | `AssistantSignals` (emit only) |
| `AssistantSignals` | Qt signal definitions | — |
| `AnimationController` | GIF cache, command→animation dispatch | `OctopusWidget`, `Config` |
| `OctopusWidget` | QPainter drawing, GIF playback | emits `animation_finished` |
| `MainWindow` | layout, worker lifecycle | wires all components |
| `actions` registry | action discovery, construction | called by `Config._load_commands` |
| `Config` | settings, `dict[str, Action]` | `actions.build()` |

---

## 4. What Is Not Changing

- `AudioWorkerThread` and `AssistantSignals` — architecture is already correct.
- `OctopusWidget` QPainter drawing code — additive changes only.
- `commands.json` syntax — fully backward compatible (`animation` field is optional).
- `AssistantEvent` StrEnum and all logging improvements from the readability pass.
- `config.env` format.

---

## 5. Build Order

1. `src/actions/base.py` — Action ABC
2. `src/actions/keyboard.py`, `daw.py`, `none.py` — migrate existing types
3. `src/actions/__init__.py` — registry + auto-discovery
4. `config.py` — remove old types, wire in `actions.build()`
5. `command_executor.py` — thin shim calling `action.execute()`
6. `Config` — remove old action types, call `actions.build()` from `_load_commands`, pass full data dict so `from_config()` can read `"animation"`
7. `OctopusWidget` — `set_audio_level()`, `play_animation()`, `animation_finished`
8. `AnimationController` — new file
9. `MainWindow` — wire in `AnimationController`, update `_on_command` and `_on_audio_level`
10. `assets/animations/` — create folder, add example GIF
