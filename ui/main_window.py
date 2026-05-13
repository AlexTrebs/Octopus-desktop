"""Main desktop window for Octopus Voice Assistant."""

import logging

from PyQt6.QtCore import Qt, QSize, QPoint, QRect
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QLinearGradient,
    QBrush,
    QFont,
    QCursor,
    QMouseEvent,
    QGuiApplication,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QCheckBox,
    QApplication,
)

from config import Config, save_config
from themes import Theme, THEMES, generate_stylesheet
from event_bridge import AssistantSignals, AudioWorkerThread
from octopus_widget import OctopusWidget
from title_bar import TitleBar
from level_meter import LevelMeter
from animation_controller import AnimationController

logger = logging.getLogger(__name__)

_RESIZE_MARGIN = 6


class MainWindow(QMainWindow):
    """Frameless main window with animated octopus, status display, and level meter."""

    def __init__(self, config: Config, parent: QWidget | None = None):
        super().__init__(parent)
        self._config = config
        self._theme = THEMES.get(config.theme, THEMES["Dark"])
        self._overlay = None  # Set by app.py after construction
        self._resizing = False
        self._resize_edge = Qt.Edge(0)
        self._drag_pos: QPoint | None = None

        # Use standard decorations on Wayland
        platform = QGuiApplication.platformName()
        if platform != "wayland":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(350, 450)
        self.resize(420, 560)
        self.setWindowTitle("Octopus Assistant")

        # Signals & audio worker
        self._signals = AssistantSignals()
        self._worker: AudioWorkerThread | None = None

        self._build_ui()
        self._connect_signals()
        self._restore_geometry()
        self._start_audio_worker()

    # -- UI construction -------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar()
        self._title_bar.set_background(self._theme.titlebar_bg)
        root_layout.addWidget(self._title_bar)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(12)

        # Octopus (expanding, centered)
        self._octopus = OctopusWidget()
        self._octopus.setSizePolicy(
            self._octopus.sizePolicy().horizontalPolicy(),
            self._octopus.sizePolicy().verticalPolicy(),
        )
        from PyQt6.QtWidgets import QSizePolicy
        self._octopus.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self._octopus, stretch=1)
        self._animation_controller = AnimationController(self._config, self._octopus)

        # Status label
        self._status_label = QLabel("Listening for wake word...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setFont(QFont("", 13))
        content_layout.addWidget(self._status_label)

        # Level meter
        self._level_meter = LevelMeter()
        content_layout.addWidget(self._level_meter)

        # Bottom bar with settings button
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        self._settings_btn = QPushButton("\u2699 Settings")
        self._settings_btn.setObjectName("accentButton")
        self._settings_btn.setFixedSize(110, 34)
        self._settings_btn.clicked.connect(self._open_settings)
        bottom_bar.addWidget(self._settings_btn)
        bottom_bar.addStretch()
        content_layout.addLayout(bottom_bar)

        root_layout.addWidget(content, stretch=1)

    def _connect_signals(self) -> None:
        self._title_bar.minimize_clicked.connect(self._switch_to_overlay)
        self._title_bar.maximize_clicked.connect(self._toggle_maximize)
        self._title_bar.close_clicked.connect(self._handle_close)

        self._signals.wake_word_detected.connect(self._on_wake_word)
        self._signals.command_recognized.connect(self._on_command)
        self._signals.command_timeout.connect(self._on_timeout)
        self._signals.state_changed.connect(self._on_state_change)
        self._signals.audio_level.connect(self._on_audio_level)
        self._signals.error_occurred.connect(self._on_error)

    # -- Audio worker ----------------------------------------------------------

    def _start_audio_worker(self) -> None:
        device_index = self._resolve_device_index()
        self._worker = AudioWorkerThread(self._config, device_index, self._signals)
        self._worker.start()

    def _resolve_device_index(self) -> int | None:
        """Look up saved device name, or auto-select a sensible default for GUI."""
        try:
            from audio_devices import create_pyaudio, get_input_devices
            pa = create_pyaudio()
            devices = get_input_devices(pa)
            pa.terminate()
        except Exception:
            return None

        # Use saved device if it exists
        if self._config.input_device_name:
            for dev in devices:
                if dev["description"] == self._config.input_device_name:
                    return dev["index"]

        # Auto-select: prefer 'default', then 'pulse', then first non-loopback
        for preferred in ("default", "pulse", "pipewire"):
            for dev in devices:
                if dev["description"] == preferred:
                    return dev["index"]
        for dev in devices:
            if "monitor" not in dev["description"].lower():
                return dev["index"]
        return None

    def stop_audio_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._worker.wait(3000)
            self._worker = None

    def restart_audio_worker(self) -> None:
        self.stop_audio_worker()
        self._start_audio_worker()

    # -- Signal handlers -------------------------------------------------------

    def _on_wake_word(self) -> None:
        self._octopus.set_state("listening")
        self._status_label.setText("Listening...")
        if self._overlay and not self.isVisible():
            self._overlay.show_animated()

    def _on_command(self, name: str) -> None:
        self._status_label.setText(f"Command: {name}")
        self._animation_controller.on_command(name)

    def _on_timeout(self) -> None:
        self._return_to_idle()
        self._status_label.setText("Timed out - listening for wake word...")

    def _on_state_change(self, state: str) -> None:
        if state == "sleeping":
            self._return_to_idle()

    def _on_audio_level(self, level: float) -> None:
        self._level_meter.set_level(level)
        self._octopus.set_audio_level(level)

    def _on_error(self, msg: str) -> None:
        self._status_label.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Audio Error", msg)

    def _return_to_idle(self) -> None:
        self._octopus.set_state("idle")
        self._status_label.setText("Listening for wake word...")
        if self._overlay:
            self._overlay.schedule_hide()

    # -- Window actions --------------------------------------------------------

    def _switch_to_overlay(self) -> None:
        if self._overlay:
            self.hide()
            self._overlay.enter_overlay_mode()

    def show_from_overlay(self) -> None:
        """Called when user clicks the overlay to return to desktop mode."""
        self.show()
        self.activateWindow()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _handle_close(self) -> None:
        behavior = self._config.close_behavior
        if behavior == "minimize":
            self._switch_to_overlay()
            return
        if behavior == "quit":
            self._quit()
            return

        # "ask" mode — show dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Close Octopus")
        dialog.setText("What would you like to do?")
        minimize_btn = dialog.addButton("Minimize to Overlay", QMessageBox.ButtonRole.AcceptRole)
        quit_btn = dialog.addButton("Quit", QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        remember_cb = QCheckBox("Remember my choice")
        dialog.setCheckBox(remember_cb)

        dialog.exec()
        clicked = dialog.clickedButton()

        if clicked == minimize_btn:
            if remember_cb.isChecked():
                self._config.close_behavior = "minimize"
                save_config(self._config)
            self._switch_to_overlay()
        elif clicked == quit_btn:
            if remember_cb.isChecked():
                self._config.close_behavior = "quit"
                save_config(self._config)
            self._quit()

    def _quit(self) -> None:
        self._save_geometry()
        self.stop_audio_worker()
        QApplication.instance().quit()

    def _open_settings(self) -> None:
        from settings_panel import SettingsPanel
        panel = SettingsPanel(self._config, self._theme, self._signals, self)
        panel.theme_changed.connect(self._apply_theme)
        panel.worker_restart_requested.connect(self.restart_audio_worker)
        panel.exec()

    def _apply_theme(self, theme_name: str) -> None:
        self._theme = THEMES.get(theme_name, THEMES["Dark"])
        self._config.theme = theme_name
        save_config(self._config)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(generate_stylesheet(self._theme))
        self._title_bar.set_background(self._theme.titlebar_bg)
        self._octopus.set_theme(self._theme)
        self.update()

    # -- Geometry save/restore -------------------------------------------------

    def _save_geometry(self) -> None:
        geo = self.geometry()
        # Stored as window x,y,w,h in the overlay position fields is wrong.
        # Store separately — we'll just let Qt handle this for now.
        pass

    def _restore_geometry(self) -> None:
        # Center on screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.move(
                avail.x() + (avail.width() - self.width()) // 2,
                avail.y() + (avail.height() - self.height()) // 2,
            )

    # -- Painting (gradient background) ----------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = self.rect()
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor(self._theme.bg_start))
        gradient.setColorAt(1, QColor(self._theme.bg_end))
        painter.fillRect(rect, QBrush(gradient))
        painter.end()

    # -- Resize handles (frameless) --------------------------------------------

    def _edge_at(self, pos: QPoint) -> Qt.Edge:
        rect = self.rect()
        edges = Qt.Edge(0)
        if pos.x() < _RESIZE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() > rect.width() - _RESIZE_MARGIN:
            edges |= Qt.Edge.RightEdge
        if pos.y() < _RESIZE_MARGIN:
            edges |= Qt.Edge.TopEdge
        elif pos.y() > rect.height() - _RESIZE_MARGIN:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._edge_at(event.pos())
            if edges:
                self._resizing = True
                self._resize_edge = edges
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resizing and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._drag_pos = event.globalPosition().toPoint()
            geo = self.geometry()

            if self._resize_edge & Qt.Edge.LeftEdge:
                geo.setLeft(geo.left() + delta.x())
            if self._resize_edge & Qt.Edge.RightEdge:
                geo.setRight(geo.right() + delta.x())
            if self._resize_edge & Qt.Edge.TopEdge:
                geo.setTop(geo.top() + delta.y())
            if self._resize_edge & Qt.Edge.BottomEdge:
                geo.setBottom(geo.bottom() + delta.y())

            if geo.width() >= self.minimumWidth() and geo.height() >= self.minimumHeight():
                self.setGeometry(geo)
            event.accept()
            return

        # Update cursor shape on edge hover
        edges = self._edge_at(event.pos())
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif edges:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        else:
            self.unsetCursor()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._resizing = False
        self._resize_edge = Qt.Edge(0)
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        event.ignore()
        self._handle_close()

    @property
    def signals(self) -> AssistantSignals:
        return self._signals
