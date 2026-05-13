"""Tests for THEMES dict and generate_stylesheet()."""


def test_themes_contains_expected_keys():
    from themes import THEMES
    for key in ("Dark", "Light", "Cyberpunk", "Ocean", "Forest"):
        assert key in THEMES


def test_theme_name_matches_key():
    from themes import THEMES
    for key, theme in THEMES.items():
        assert theme.name == key


def test_generate_stylesheet_returns_nonempty_string():
    from themes import THEMES, generate_stylesheet
    css = generate_stylesheet(THEMES["Dark"])
    assert isinstance(css, str)
    assert len(css) > 200


def test_generate_stylesheet_interpolates_colors():
    from themes import THEMES, generate_stylesheet
    theme = THEMES["Dark"]
    css = generate_stylesheet(theme)
    assert theme.accent in css
    assert theme.text_primary in css
    assert theme.button_bg in css


def test_generate_stylesheet_all_themes():
    from themes import THEMES, generate_stylesheet
    for theme in THEMES.values():
        css = generate_stylesheet(theme)
        assert theme.accent in css


def test_octopus_state_colors_are_hex():
    from themes import OCTOPUS_IDLE, OCTOPUS_LISTENING, OCTOPUS_PROCESSING
    for color in (OCTOPUS_IDLE, OCTOPUS_LISTENING, OCTOPUS_PROCESSING):
        assert color.startswith("#")
        assert len(color) == 7
