"""Tests for TitleBar signals and mouse drag."""


def test_minimize_button_emits_signal(qtbot):
    from title_bar import TitleBar
    bar = TitleBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.minimize_clicked, timeout=1000):
        bar._minimize_btn.click()


def test_maximize_button_emits_signal(qtbot):
    from title_bar import TitleBar
    bar = TitleBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.maximize_clicked, timeout=1000):
        bar._maximize_btn.click()


def test_close_button_emits_signal(qtbot):
    from title_bar import TitleBar
    bar = TitleBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.close_clicked, timeout=1000):
        bar._close_btn.click()


def test_set_background_applies_style(qtbot):
    from title_bar import TitleBar
    bar = TitleBar()
    qtbot.addWidget(bar)
    bar.set_background("#FF0000")
    assert "#FF0000" in bar.styleSheet()


def test_initial_drag_pos_is_none(qtbot):
    from title_bar import TitleBar
    bar = TitleBar()
    qtbot.addWidget(bar)
    assert bar._drag_pos is None


def test_mouse_press_sets_drag_pos(qtbot):
    from title_bar import TitleBar
    from PyQt6.QtCore import Qt, QPoint
    bar = TitleBar()
    bar.show()
    qtbot.addWidget(bar)
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert bar._drag_pos is not None


def test_mouse_release_clears_drag_pos(qtbot):
    from title_bar import TitleBar
    from PyQt6.QtCore import Qt, QPoint
    bar = TitleBar()
    bar.show()
    qtbot.addWidget(bar)
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    qtbot.mouseRelease(bar, Qt.MouseButton.LeftButton)
    assert bar._drag_pos is None


def test_double_click_emits_maximize(qtbot):
    from title_bar import TitleBar
    from PyQt6.QtCore import Qt
    bar = TitleBar()
    bar.show()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.maximize_clicked, timeout=1000):
        qtbot.mouseDClick(bar, Qt.MouseButton.LeftButton)
