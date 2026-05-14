"""System tray icon with context menu."""

from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QWidget
from PyQt6.QtCore import QSize


def _create_icon() -> QIcon:
    """Generate a simple octopus-colored circle icon."""
    size = 64
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor("#8B5CF6")))
    painter.setPen(QColor("#8B5CF6"))
    painter.drawEllipse(4, 4, size - 8, size - 8)
    painter.end()

    return QIcon(pixmap)


def create_tray_icon(
    app: QApplication,
    window: QWidget,
    overlay: QWidget,
) -> QSystemTrayIcon:
    """Create and configure the system tray icon."""
    tray = QSystemTrayIcon(app)
    tray.setIcon(_create_icon())
    tray.setToolTip("Octopus Assistant")

    menu = QMenu()

    def show_window():
        overlay.leave_overlay_mode()
        window.show()
        window.activateWindow()

    def quit_app():
        window.stop_audio_worker()
        app.quit()

    show_action = QAction("Show Window", menu)
    show_action.triggered.connect(show_window)
    menu.addAction(show_action)

    hide_action = QAction("Hide Window", menu)
    hide_action.triggered.connect(window.hide)
    menu.addAction(hide_action)

    menu.addSeparator()

    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(quit_app)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            show_window()

    tray.activated.connect(on_tray_activated)

    return tray
