"""Animated octopus widget drawn with QPainter."""

import math
import random

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QPainterPath,
    QPen,
    QBrush,
    QMovie,
)
from PyQt6.QtWidgets import QWidget

from themes import OCTOPUS_IDLE, OCTOPUS_LISTENING, OCTOPUS_PROCESSING, Theme


class OctopusWidget(QWidget):
    """Animated octopus that responds to assistant state changes."""

    animation_finished = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = "idle"
        self._phase = 0.0
        self._glow_phase = 0.0
        self._blink_timer = 0.0
        self._is_blinking = False
        self._blink_cooldown = random.uniform(3.0, 7.0)

        self._color = QColor(OCTOPUS_IDLE)
        self._target_color = QColor(OCTOPUS_IDLE)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(33)  # ~30fps

        self.setMinimumSize(80, 80)

        self._movie: QMovie | None = None
        self._live_amplitude: float = 0.0

    def set_state(self, state: str) -> None:
        self._state = state
        if state == "idle":
            self._target_color = QColor(OCTOPUS_IDLE)
        elif state == "listening":
            self._target_color = QColor(OCTOPUS_LISTENING)
        elif state == "processing":
            self._target_color = QColor(OCTOPUS_PROCESSING)

    def set_theme(self, theme: Theme) -> None:
        # Theme doesn't change octopus colors (they're consistent), but
        # this hook is available for future customization.
        pass

    def set_audio_level(self, db: float) -> None:
        # Map dB range [-60, 0] to amplitude multiplier [0, 1]
        self._live_amplitude = max(0.0, min(1.0, (db + 60) / 60))

    def play_animation(self, movie: QMovie) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.frameChanged.disconnect(self.update)
            self._movie.finished.disconnect(self._on_animation_finished)
        self._movie = movie
        self._movie.frameChanged.connect(self.update)
        self._movie.finished.connect(self._on_animation_finished)
        self._movie.start()

    def _on_animation_finished(self) -> None:
        movie = self._movie
        self._movie = None
        if movie is not None:
            movie.frameChanged.disconnect(self.update)
            movie.finished.disconnect(self._on_animation_finished)
        self.animation_finished.emit()
        self.update()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(200, 200)

    def _tick(self) -> None:
        dt = 0.033
        if self._state == "idle":
            self._phase += dt * 1.5
        elif self._state == "listening":
            self._phase += dt * 3.0
        elif self._state == "processing":
            self._phase += dt * 5.0

        self._glow_phase += dt * 2.0

        # Blink logic
        self._blink_timer += dt
        if self._is_blinking:
            if self._blink_timer > 0.15:
                self._is_blinking = False
                self._blink_timer = 0.0
                self._blink_cooldown = random.uniform(3.0, 7.0)
        else:
            if self._blink_timer > self._blink_cooldown:
                self._is_blinking = True
                self._blink_timer = 0.0

        # Smooth color transition
        self._color = _lerp_color(self._color, self._target_color, 0.1)

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._movie is not None:
            pixmap = self._movie.currentPixmap()
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                return

        w = self.width()
        h = self.height()
        size = min(w, h)
        cx = w / 2
        cy = h / 2

        scale = size / 200.0
        painter.translate(cx, cy)
        painter.scale(scale, scale)

        self._draw_glow(painter)
        self._draw_tentacles(painter)
        self._draw_body(painter)
        self._draw_eyes(painter)

        painter.end()

    def _draw_glow(self, painter: QPainter) -> None:
        if self._state == "idle":
            return

        glow_alpha = int(30 + 20 * math.sin(self._glow_phase))
        if self._state == "processing":
            glow_alpha = int(50 + 30 * math.sin(self._glow_phase))

        glow_color = QColor(self._color)
        glow_color.setAlpha(glow_alpha)

        radius = 90 + 10 * math.sin(self._glow_phase * 0.7)
        gradient = QRadialGradient(QPointF(0, -10), radius)
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(-radius, -radius - 10, radius * 2, radius * 2))

    def _draw_body(self, painter: QPainter) -> None:
        body_rect = QRectF(-40, -55, 80, 70)

        gradient = QRadialGradient(QPointF(0, -30), 60)
        lighter = QColor(self._color)
        lighter.setAlpha(255)
        darker = QColor(self._color).darker(140)
        gradient.setColorAt(0, lighter)
        gradient.setColorAt(1, darker)

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(body_rect)

    def _draw_tentacles(self, painter: QPainter) -> None:
        num_tentacles = 8
        tentacle_color = QColor(self._color).darker(120)

        for i in range(num_tentacles):
            angle_offset = (i / num_tentacles) * math.pi - math.pi / 2
            start_x = 35 * math.cos(angle_offset + math.pi / 2)
            start_y = 10

            wave_speed = self._phase
            base_amp = {"idle": 8, "listening": 12, "processing": 16}.get(self._state, 8)
            wave_amp = base_amp + self._live_amplitude * 10

            path = QPainterPath()
            path.moveTo(start_x, start_y)

            # Three bezier segments for each tentacle
            length = 50
            seg_len = length / 3
            for seg in range(3):
                t = seg / 3.0
                wave = wave_amp * math.sin(wave_speed + i * 0.8 + t * 4)
                dx = wave * (1 + seg * 0.3)

                cy1 = start_y + seg_len * seg + seg_len * 0.5
                cy2 = start_y + seg_len * (seg + 1)
                cx1 = start_x + dx
                cx2 = start_x + dx * 0.6
                end_x = start_x + dx * 0.3
                end_y = cy2

                path.cubicTo(cx1, cy1, cx2, cy2, end_x, end_y)

            # Taper the tentacle width
            pen_width = max(2, 5 - seg)
            pen = QPen(tentacle_color, pen_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def _draw_eyes(self, painter: QPainter) -> None:
        eye_color = QColor("#FFFFFF")
        pupil_color = QColor("#1a0f2e")

        eye_y = -35
        eye_spacing = 16
        eye_w = 10
        eye_h = 12 if not self._is_blinking else 2

        for side in (-1, 1):
            eye_x = side * eye_spacing

            # White of eye
            painter.setBrush(QBrush(eye_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(eye_x - eye_w / 2, eye_y - eye_h / 2, eye_w, eye_h)
            )

            # Pupil
            if not self._is_blinking:
                pupil_size = 5
                painter.setBrush(QBrush(pupil_color))
                painter.drawEllipse(
                    QRectF(
                        eye_x - pupil_size / 2,
                        eye_y - pupil_size / 2,
                        pupil_size,
                        pupil_size,
                    )
                )


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )
