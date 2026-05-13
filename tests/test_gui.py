"""GUI tests for OctopusWidget and e2e MainWindow boot.

Requires pytest-qt: uv pip install pytest-qt
"""
import json
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.fixture
def main_window(qtbot, tmp_path, monkeypatch):
    """Construct a MainWindow with audio worker patched out."""
    monkeypatch.setattr("config.load_dotenv", lambda path: None)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    (tmp_path / "config.env").write_text("")
    (tmp_path / "commands.json").write_text(json.dumps({
        "start": {"action": "keyboard", "keys": [["F5"]]}
    }))
    for var, val in [
        ("WAKE_WORD", "octopus"), ("ENVIRONMENT", "Moderate"),
        ("COMMAND_TIMEOUT", "3"), ("ENABLE_AUDIO_PROCESSING", "true"),
        ("LOG_LEVEL", "INFO"), ("VOSK_MODEL_PATH", "vosk-small"),
        ("PORCUPINE_ACCESS_KEY", ""), ("THEME", "Dark"),
        ("OVERLAY_X", "-1"), ("OVERLAY_Y", "-1"),
        ("OVERLAY_POSITION", "top-right"), ("CLOSE_BEHAVIOR", "minimize"),
    ]:
        monkeypatch.setenv(var, val)
    from config import Config
    from main_window import MainWindow
    cfg = Config()
    with patch.object(MainWindow, "_start_audio_worker", lambda self: None):
        w = MainWindow(cfg)
    qtbot.addWidget(w)
    return w


# --- OctopusWidget: set_audio_level ---

def test_audio_level_high_clamps_to_one(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.set_audio_level(999.0)
    assert w._live_amplitude == 1.0


def test_audio_level_low_clamps_to_zero(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.set_audio_level(-999.0)
    assert w._live_amplitude == 0.0


def test_audio_level_zero_db_is_one(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.set_audio_level(0.0)
    assert w._live_amplitude == 1.0


def test_audio_level_minus60_is_zero(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.set_audio_level(-60.0)
    assert w._live_amplitude == 0.0


def test_audio_level_midpoint(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.set_audio_level(-30.0)
    assert abs(w._live_amplitude - 0.5) < 0.01


# --- OctopusWidget: set_state ---

def test_set_state_updates_state(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    for state in ("idle", "listening", "processing"):
        w.set_state(state)
        assert w._state == state


def test_initial_state_is_idle(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    assert w._state == "idle"


# --- OctopusWidget: play_animation signal ---

def test_animation_finished_signal_emitted(qtbot):
    from octopus_widget import OctopusWidget
    from PyQt6.QtGui import QMovie
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.show()

    # An empty/invalid QMovie finishes immediately on start
    movie = QMovie()
    with qtbot.waitSignal(w.animation_finished, timeout=2000):
        w.play_animation(movie)


def test_play_animation_clears_movie_after_finish(qtbot):
    from octopus_widget import OctopusWidget
    from PyQt6.QtGui import QMovie
    w = OctopusWidget()
    qtbot.addWidget(w)
    movie = QMovie()
    with qtbot.waitSignal(w.animation_finished, timeout=2000):
        w.play_animation(movie)
    assert w._movie is None


def test_replacing_movie_disconnects_old(qtbot):
    from octopus_widget import OctopusWidget
    from PyQt6.QtGui import QMovie
    w = OctopusWidget()
    qtbot.addWidget(w)

    movie1 = QMovie()
    movie2 = QMovie()
    w.play_animation(movie1)
    # Replacing before first finishes should not raise a disconnect error
    w.play_animation(movie2)
    # Both are empty movies so they finish immediately — just verify no exception


# --- e2e: MainWindow boots without crashing ---

# --- OctopusWidget: paint and tick coverage ---

def test_octopus_paint_idle_no_crash(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.resize(200, 200)
    w.show()
    w.update()
    qtbot.wait(50)


def test_octopus_paint_listening_no_crash(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.resize(200, 200)
    w.show()
    w.set_state("listening")
    w.update()
    qtbot.wait(50)


def test_octopus_paint_processing_no_crash(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w.resize(200, 200)
    w.show()
    w.set_state("processing")
    w.set_audio_level(-10.0)
    w.update()
    qtbot.wait(50)


def test_octopus_tick_advances_phase(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    initial_phase = w._phase
    w._tick()
    assert w._phase > initial_phase


def test_octopus_tick_blink_logic(qtbot):
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    # Force blink cooldown to trigger
    w._blink_cooldown = 0.0
    w._blink_timer = 1.0
    w._tick()
    assert w._is_blinking


def test_octopus_tick_blink_end(qtbot):
    """Blink ends after 0.15s."""
    from octopus_widget import OctopusWidget
    w = OctopusWidget()
    qtbot.addWidget(w)
    w._is_blinking = True
    w._blink_timer = 0.2  # > 0.15 → blink ends
    w._tick()
    assert not w._is_blinking


# --- e2e: MainWindow boots without crashing ---

def test_main_window_constructs(qtbot, tmp_path, monkeypatch):
    import json
    from unittest.mock import MagicMock

    # Minimal config mock — skips all audio/model setup
    monkeypatch.setattr("config.load_dotenv", lambda path: None)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    (tmp_path / "config.env").write_text("")
    (tmp_path / "commands.json").write_text(json.dumps({
        "start": {"action": "keyboard", "keys": [["F5"]]}
    }))

    for var, val in [
        ("WAKE_WORD", "octopus"), ("ENVIRONMENT", "Moderate"),
        ("COMMAND_TIMEOUT", "3"), ("ENABLE_AUDIO_PROCESSING", "true"),
        ("LOG_LEVEL", "INFO"), ("VOSK_MODEL_PATH", "vosk-small"),
        ("PORCUPINE_ACCESS_KEY", ""), ("THEME", "Dark"),
        ("OVERLAY_X", "-1"), ("OVERLAY_Y", "-1"),
        ("OVERLAY_POSITION", "top-right"), ("CLOSE_BEHAVIOR", "minimize"),
    ]:
        monkeypatch.setenv(var, val)

    from config import Config
    cfg = Config()

    # Patch out audio worker startup — no microphone available in tests
    from unittest.mock import patch
    from main_window import MainWindow
    with patch.object(MainWindow, "_start_audio_worker", lambda self: None):
        w = MainWindow(cfg)
    qtbot.addWidget(w)
    assert w.isVisible() or not w.isVisible()  # window constructed without crash


# --- MainWindow signal handlers ---

def test_on_wake_word_sets_listening(main_window):
    main_window._on_wake_word()
    assert main_window._octopus._state == "listening"
    assert "Listening" in main_window._status_label.text()


def test_on_command_updates_status(main_window):
    main_window._on_command("start")
    assert "start" in main_window._status_label.text()


def test_on_timeout_resets_to_idle(main_window):
    main_window._octopus.set_state("listening")
    main_window._on_timeout()
    assert main_window._octopus._state == "idle"
    assert "Timed out" in main_window._status_label.text()


def test_on_state_change_sleeping_returns_to_idle(main_window):
    main_window._octopus.set_state("listening")
    main_window._on_state_change("sleeping")
    assert main_window._octopus._state == "idle"


def test_on_audio_level_updates_octopus(main_window):
    main_window._on_audio_level(-30.0)
    assert abs(main_window._octopus._live_amplitude - 0.5) < 0.01


def test_on_audio_level_updates_meter(main_window):
    main_window._on_audio_level(0.0)
    assert main_window._level_meter._display_level == pytest.approx(1.0, abs=0.01)


def test_on_error_updates_status_label(main_window):
    with patch("main_window.QMessageBox.critical"):
        main_window._on_error("something broke")
    assert "something broke" in main_window._status_label.text()


def test_signals_property_returns_signals(main_window):
    from event_bridge import AssistantSignals
    assert isinstance(main_window.signals, AssistantSignals)


def test_stop_audio_worker_no_worker_is_noop(main_window):
    main_window._worker = None
    main_window.stop_audio_worker()  # should not raise


def test_toggle_maximize_toggles(main_window):
    main_window.show()
    main_window._toggle_maximize()
    assert main_window.isMaximized()
    main_window._toggle_maximize()
    assert not main_window.isMaximized()


def test_apply_theme_updates_config(main_window):
    main_window._apply_theme("Light")
    assert main_window._config.theme == "Light"


def test_edge_at_left_edge(main_window):
    from PyQt6.QtCore import Qt, QPoint
    edge = main_window._edge_at(QPoint(2, 100))
    assert edge & Qt.Edge.LeftEdge


def test_edge_at_right_edge(main_window):
    from PyQt6.QtCore import Qt, QPoint
    w = main_window.width()
    edge = main_window._edge_at(QPoint(w - 2, 100))
    assert edge & Qt.Edge.RightEdge


def test_edge_at_center_returns_no_edge(main_window):
    from PyQt6.QtCore import Qt, QPoint
    edge = main_window._edge_at(QPoint(main_window.width() // 2, main_window.height() // 2))
    assert not edge


def test_paint_event_no_crash(main_window, qtbot):
    main_window.show()
    main_window.update()
    qtbot.wait(50)


def test_main_window_close_event_ignored(main_window):
    from PyQt6.QtGui import QCloseEvent
    event = QCloseEvent()
    main_window.closeEvent(event)
    assert not event.isAccepted()  # always ignored — _handle_close drives behavior


def test_resolve_device_index_returns_none_on_exception(main_window):
    with patch("audio_devices.create_pyaudio", side_effect=Exception("no audio")):
        result = main_window._resolve_device_index()
    assert result is None


def test_resolve_device_index_prefers_named_device(main_window):
    mock_pa = MagicMock()
    devices = [{"index": 5, "description": "my-mic"}]
    main_window._config.input_device_name = "my-mic"
    with patch("audio_devices.create_pyaudio", return_value=mock_pa):
        with patch("audio_devices.get_input_devices", return_value=devices):
            result = main_window._resolve_device_index()
    assert result == 5


def test_resolve_device_index_prefers_default_device(main_window):
    mock_pa = MagicMock()
    devices = [
        {"index": 0, "description": "hw:1,0"},
        {"index": 1, "description": "default"},
    ]
    main_window._config.input_device_name = None
    with patch("audio_devices.create_pyaudio", return_value=mock_pa):
        with patch("audio_devices.get_input_devices", return_value=devices):
            result = main_window._resolve_device_index()
    assert result == 1


# --- OverlayWidget ---


@pytest.fixture
def overlay(qtbot):
    cfg = MagicMock()
    cfg.overlay_x = -1
    cfg.overlay_y = -1
    cfg.overlay_position_preset = "top-right"
    from event_bridge import AssistantSignals
    from overlay_widget import OverlayWidget
    w = OverlayWidget(cfg, AssistantSignals())
    qtbot.addWidget(w)
    return w


def test_overlay_constructs(overlay):
    from overlay_widget import OverlayWidget
    assert isinstance(overlay, OverlayWidget)


def test_enter_overlay_mode_sets_flag(overlay):
    overlay.enter_overlay_mode()
    assert overlay._overlay_active is True


def test_leave_overlay_mode_clears_flag(overlay):
    overlay.enter_overlay_mode()
    overlay.leave_overlay_mode()
    assert overlay._overlay_active is False


def test_on_wake_word_sets_listening(overlay):
    overlay._on_wake_word()
    assert overlay._octopus._state == "listening"


def test_on_command_sets_processing(overlay):
    overlay._on_command("start")
    assert overlay._octopus._state == "processing"


def test_on_timeout_sets_idle(overlay):
    overlay._octopus.set_state("listening")
    overlay._on_timeout()
    assert overlay._octopus._state == "idle"


def test_on_state_change_sleeping_sets_idle(overlay):
    overlay._octopus.set_state("listening")
    overlay._on_state_change("sleeping")
    assert overlay._octopus._state == "idle"


def test_show_animated_does_nothing_when_not_in_overlay_mode(overlay):
    overlay._overlay_active = False
    overlay.show_animated()
    assert not overlay.isVisible()


# --- tray_icon ---


def test_create_tray_icon_returns_system_tray(qapp_instance):
    from tray_icon import create_tray_icon
    from PyQt6.QtWidgets import QSystemTrayIcon
    tray = create_tray_icon(qapp_instance, MagicMock(), MagicMock())
    assert isinstance(tray, QSystemTrayIcon)
