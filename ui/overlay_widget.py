"""Floating overlay widget — minimal octopus popup on wake word detection."""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal, QEasingCurve
from PyQt6.QtGui import QGuiApplication, QMouseEvent, QAction
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu, QApplication

from config import Config
from event_bridge import AssistantSignals
from octopus_widget import OctopusWidget


class OverlayWidget(QWidget):
    """Frameless, always-on-top floating octopus overlay."""

    show_window_requested = pyqtSignal()

    def __init__(
        self,
        config: Config,
        signals: AssistantSignals,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._config = config
        self._signals = signals
        self._overlay_active = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_hide)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(100, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self._octopus = OctopusWidget()
        self._octopus.setFixedSize(80, 80)
        layout.addWidget(self._octopus)

        self._slide_anim = QPropertyAnimation(self, b"geometry")
        self._slide_anim.setDuration(250)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Connect assistant signals
        self._signals.wake_word_detected.connect(self._on_wake_word)
        self._signals.command_recognized.connect(self._on_command)
        self._signals.command_timeout.connect(self._on_timeout)
        self._signals.state_changed.connect(self._on_state_change)

    def enter_overlay_mode(self) -> None:
        """Switch from desktop mode to overlay mode."""
        self._overlay_active = True

    def leave_overlay_mode(self) -> None:
        """Switch from overlay mode back to desktop mode."""
        self._overlay_active = False
        self.hide()

    def show_animated(self) -> None:
        """Show the overlay with a slide-in animation."""
        if not self._overlay_active:
            return

        self._hide_timer.stop()
        target = self._target_position()
        # Start off-screen to the right and slide in
        start = QRect(target)
        start.moveLeft(target.x() + 120)

        self._slide_anim.setStartValue(start)
        self._slide_anim.setEndValue(target)
        self.show()
        self._slide_anim.start()

    def schedule_hide(self) -> None:
        """Hide overlay after a short delay."""
        if self._overlay_active and self.isVisible():
            self._hide_timer.start(1200)

    def _do_hide(self) -> None:
        if self._overlay_active:
            self.hide()

    def _target_position(self) -> QRect:
        """Calculate overlay position from config or preset."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return QRect(100, 100, 100, 100)

        avail = screen.availableGeometry()
        w, h = 100, 100

        # Custom position
        if self._config.overlay_x >= 0 and self._config.overlay_y >= 0:
            return QRect(self._config.overlay_x, self._config.overlay_y, w, h)

        # Preset positions
        margin = 20
        preset = self._config.overlay_position_preset
        if preset == "top-left":
            x, y = avail.x() + margin, avail.y() + margin
        elif preset == "bottom-left":
            x, y = avail.x() + margin, avail.y() + avail.height() - h - margin
        elif preset == "bottom-right":
            x, y = avail.x() + avail.width() - w - margin, avail.y() + avail.height() - h - margin
        else:  # top-right (default)
            x, y = avail.x() + avail.width() - w - margin, avail.y() + margin

        return QRect(x, y, w, h)

    # -- Signal handlers -------------------------------------------------------

    def _on_wake_word(self) -> None:
        self._octopus.set_state("listening")
        self.show_animated()

    def _on_command(self, name: str) -> None:
        self._octopus.set_state("processing")
        self.schedule_hide()

    def _on_timeout(self) -> None:
        self._octopus.set_state("idle")
        self.schedule_hide()

    def _on_state_change(self, state: str) -> None:
        if state == "sleeping":
            self._octopus.set_state("idle")

    # -- Mouse events ----------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.leave_overlay_mode()
            self.show_window_requested.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)

    def _show_context_menu(self, event: QMouseEvent) -> None:
        menu = QMenu(self)

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self._context_show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPosition().toPoint())

    def _context_show_window(self) -> None:
        self.leave_overlay_mode()
        self.show_window_requested.emit()
