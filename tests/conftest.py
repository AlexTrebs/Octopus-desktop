import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp_instance():
    """Session-scoped QApplication for tests that need Qt but don't use qtbot."""
    return QApplication.instance() or QApplication([])
