"""Custom frameless title bar with window controls."""

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QMouseEvent, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)


class TitleBar(QWidget):
    """Custom title bar with minimize (to overlay), maximize, and close buttons."""

    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Icon placeholder (small circle)
        icon_label = QLabel("\U0001F419")
        icon_label.setFont(QFont("", 16))
        layout.addWidget(icon_label)

        # Title
        self._title = QLabel("Octopus Assistant")
        self._title.setFont(QFont("", 12, QFont.Weight.DemiBold))
        layout.addWidget(self._title)

        layout.addStretch()

        # Window controls
        btn_style_base = """
            QPushButton {
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 4px 8px;
            }
        """

        self._minimize_btn = QPushButton("\u2500")
        self._minimize_btn.setFixedSize(32, 28)
        self._minimize_btn.setStyleSheet(
            btn_style_base + "QPushButton:hover { background-color: rgba(255,255,255,0.1); }"
        )
        self._minimize_btn.setToolTip("Minimize to overlay")
        self._minimize_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self._minimize_btn)

        self._maximize_btn = QPushButton("\u25A1")
        self._maximize_btn.setFixedSize(32, 28)
        self._maximize_btn.setStyleSheet(
            btn_style_base + "QPushButton:hover { background-color: rgba(255,255,255,0.1); }"
        )
        self._maximize_btn.setToolTip("Maximize / Restore")
        self._maximize_btn.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(self._maximize_btn)

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setObjectName("closeButton")
        self._close_btn.setFixedSize(32, 28)
        self._close_btn.setStyleSheet(
            btn_style_base + "QPushButton:hover { background-color: #DC2626; color: white; }"
        )
        self._close_btn.setToolTip("Close")
        self._close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self._close_btn)

    def set_background(self, color: str) -> None:
        self.setStyleSheet(f"TitleBar {{ background-color: {color}; }}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
