"""Tests for LevelMeter widget."""
import pytest


def test_set_level_zero_db_is_one(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    assert w._display_level == pytest.approx(1.0, abs=0.01)


def test_set_level_minus60_is_zero(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(-60.0)
    assert w._display_level == pytest.approx(0.0, abs=0.01)


def test_set_level_clamps_below_range(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(-200.0)
    assert w._display_level >= 0.0


def test_set_level_clamps_above_range(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(10.0)
    assert w._display_level <= 1.0


def test_set_level_only_increases_display_level(qtbot):
    """Display level never drops on set_level — only decays via timer."""
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    high = w._display_level
    w.set_level(-60.0)
    assert w._display_level == high


def test_set_level_updates_peak(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    assert w._peak == pytest.approx(1.0, abs=0.01)


def test_peak_does_not_decrease_on_lower_signal(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    peak_high = w._peak
    w.set_level(-30.0)
    assert w._peak == pytest.approx(peak_high, abs=0.01)


def test_initial_levels_are_zero(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    assert w._display_level == 0.0
    assert w._peak == 0.0


def test_decay_decreases_display_level(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    w._decay()
    assert w._display_level < 1.0


def test_decay_decreases_peak(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.set_level(0.0)
    w._decay()
    assert w._peak < 1.0


def test_decay_zeros_tiny_display_level(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w._display_level = 0.0005
    w._decay()
    assert w._display_level == 0.0


def test_decay_zeros_tiny_peak(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w._peak = 0.0005
    w._decay()
    assert w._peak == 0.0


def test_paint_event_does_not_crash(qtbot):
    from level_meter import LevelMeter
    w = LevelMeter()
    qtbot.addWidget(w)
    w.resize(200, 16)
    w.show()
    w.set_level(-30.0)
    w.update()
    qtbot.wait(50)
