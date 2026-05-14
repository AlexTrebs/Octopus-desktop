"""Audio level meter widget."""

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtWidgets import QWidget


class LevelMeter(QWidget):
    """Horizontal audio level meter with smooth decay."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setMinimumWidth(120)

        self._level = -100.0  # dB
        self._display_level = 0.0  # normalized 0..1
        self._peak = 0.0

        self._decay_timer = QTimer(self)
        self._decay_timer.timeout.connect(self._decay)
        self._decay_timer.start(33)  # ~30fps

    def set_level(self, db: float) -> None:
        """Update the meter with a new level in dB."""
        self._level = db
        normalized = max(0.0, min(1.0, (db + 60.0) / 60.0))
        if normalized > self._display_level:
            self._display_level = normalized
        if normalized > self._peak:
            self._peak = normalized

    def _decay(self) -> None:
        # Smooth decay
        self._display_level *= 0.92
        self._peak *= 0.995
        if self._display_level < 0.001:
            self._display_level = 0.0
        if self._peak < 0.001:
            self._peak = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = h / 2

        # Background
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Level bar
        bar_w = w * self._display_level
        if bar_w > 1:
            gradient = QLinearGradient(0, 0, w, 0)
            gradient.setColorAt(0.0, QColor("#22C55E"))   # green
            gradient.setColorAt(0.6, QColor("#EAB308"))   # yellow
            gradient.setColorAt(1.0, QColor("#EF4444"))   # red

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(QRectF(0, 0, bar_w, h), r, r)

        # Peak indicator
        if self._peak > 0.01:
            peak_x = w * self._peak
            painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
            painter.drawRoundedRect(QRectF(peak_x - 2, 0, 3, h), 1, 1)

        painter.end()
