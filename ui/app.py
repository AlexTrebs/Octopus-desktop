"""PyQt6 application entry point for Octopus Voice Assistant."""

import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication, QIcon

from config import Config
from themes import THEMES, generate_stylesheet
from main_window import MainWindow
from overlay_widget import OverlayWidget
from tray_icon import create_tray_icon

logger = logging.getLogger(__name__)


def run_gui(config: Config) -> None:
    """Launch the full PyQt6 GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("Octopus Assistant")
    app.setQuitOnLastWindowClosed(False)

    theme = THEMES.get(config.theme, THEMES["Dark"])
    app.setStyleSheet(generate_stylesheet(theme))

    window = MainWindow(config)
    overlay = OverlayWidget(config, window.signals)

    # Cross-link window and overlay
    window._overlay = overlay
    overlay.show_window_requested.connect(window.show_from_overlay)

    # System tray
    tray = create_tray_icon(app, window, overlay)
    tray.show()

    window.show()
    sys.exit(app.exec())
