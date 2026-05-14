"""Theme definitions and stylesheet generator for Octopus UI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    # Background gradient
    bg_start: str
    bg_end: str
    # Text
    text_primary: str
    text_secondary: str
    # Accents
    accent: str
    accent_hover: str
    # Title bar
    titlebar_bg: str
    titlebar_text: str
    # Buttons
    button_bg: str
    button_hover: str
    button_text: str
    # Close button
    close_hover: str
    # Panel / card backgrounds
    panel_bg: str
    panel_border: str
    # Input fields
    input_bg: str
    input_border: str
    input_focus_border: str
    # Scrollbar
    scrollbar_bg: str
    scrollbar_handle: str
    # Settings tabs
    tab_bg: str
    tab_selected: str


# Octopus state colors (shared across all themes)
OCTOPUS_IDLE = "#8B5CF6"
OCTOPUS_LISTENING = "#C084FC"
OCTOPUS_PROCESSING = "#A78BFA"

THEMES: dict[str, Theme] = {
    "Dark": Theme(
        name="Dark",
        bg_start="#2D1B4E",
        bg_end="#1a0f2e",
        text_primary="#FFFFFF",
        text_secondary="#B0A0C8",
        accent="#8B5CF6",
        accent_hover="#A78BFA",
        titlebar_bg="#1a0f2e",
        titlebar_text="#FFFFFF",
        button_bg="#3B2667",
        button_hover="#4C3580",
        button_text="#FFFFFF",
        close_hover="#DC2626",
        panel_bg="#241540",
        panel_border="#3B2667",
        input_bg="#1a0f2e",
        input_border="#3B2667",
        input_focus_border="#8B5CF6",
        scrollbar_bg="#1a0f2e",
        scrollbar_handle="#3B2667",
        tab_bg="#241540",
        tab_selected="#3B2667",
    ),
    "Light": Theme(
        name="Light",
        bg_start="#e8f5e9",
        bg_end="#c8e6c9",
        text_primary="#1B5E20",
        text_secondary="#4CAF50",
        accent="#2E7D32",
        accent_hover="#388E3C",
        titlebar_bg="#c8e6c9",
        titlebar_text="#1B5E20",
        button_bg="#A5D6A7",
        button_hover="#81C784",
        button_text="#1B5E20",
        close_hover="#DC2626",
        panel_bg="#E8F5E9",
        panel_border="#A5D6A7",
        input_bg="#FFFFFF",
        input_border="#A5D6A7",
        input_focus_border="#2E7D32",
        scrollbar_bg="#E8F5E9",
        scrollbar_handle="#A5D6A7",
        tab_bg="#E8F5E9",
        tab_selected="#A5D6A7",
    ),
    "Cyberpunk": Theme(
        name="Cyberpunk",
        bg_start="#1A0A2E",
        bg_end="#0D0521",
        text_primary="#F0E6FF",
        text_secondary="#9D4EDD",
        accent="#FF006E",
        accent_hover="#FF3385",
        titlebar_bg="#0D0521",
        titlebar_text="#FF006E",
        button_bg="#2D1157",
        button_hover="#3D1A70",
        button_text="#FF006E",
        close_hover="#FF006E",
        panel_bg="#150833",
        panel_border="#2D1157",
        input_bg="#0D0521",
        input_border="#2D1157",
        input_focus_border="#FF006E",
        scrollbar_bg="#0D0521",
        scrollbar_handle="#2D1157",
        tab_bg="#150833",
        tab_selected="#2D1157",
    ),
    "Ocean": Theme(
        name="Ocean",
        bg_start="#0D1B2A",
        bg_end="#1B2838",
        text_primary="#E0F7FA",
        text_secondary="#4DD0E1",
        accent="#0097A7",
        accent_hover="#00ACC1",
        titlebar_bg="#0D1B2A",
        titlebar_text="#E0F7FA",
        button_bg="#1A3A50",
        button_hover="#234B65",
        button_text="#E0F7FA",
        close_hover="#DC2626",
        panel_bg="#152535",
        panel_border="#1A3A50",
        input_bg="#0D1B2A",
        input_border="#1A3A50",
        input_focus_border="#0097A7",
        scrollbar_bg="#0D1B2A",
        scrollbar_handle="#1A3A50",
        tab_bg="#152535",
        tab_selected="#1A3A50",
    ),
    "Forest": Theme(
        name="Forest",
        bg_start="#1B2E1B",
        bg_end="#0F1F0F",
        text_primary="#E8F5E9",
        text_secondary="#81C784",
        accent="#4CAF50",
        accent_hover="#66BB6A",
        titlebar_bg="#0F1F0F",
        titlebar_text="#E8F5E9",
        button_bg="#2E4B2E",
        button_hover="#3D613D",
        button_text="#E8F5E9",
        close_hover="#DC2626",
        panel_bg="#1B2E1B",
        panel_border="#2E4B2E",
        input_bg="#0F1F0F",
        input_border="#2E4B2E",
        input_focus_border="#4CAF50",
        scrollbar_bg="#0F1F0F",
        scrollbar_handle="#2E4B2E",
        tab_bg="#1B2E1B",
        tab_selected="#2E4B2E",
    ),
}


def generate_stylesheet(theme: Theme) -> str:
    """Generate a full Qt stylesheet from a theme."""
    return f"""
        QWidget {{
            color: {theme.text_primary};
            font-family: "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
            font-size: 13px;
        }}
        QLabel {{
            color: {theme.text_primary};
            background: transparent;
        }}
        QLabel#secondaryLabel {{
            color: {theme.text_secondary};
        }}
        QPushButton {{
            background-color: {theme.button_bg};
            color: {theme.button_text};
            border: 1px solid {theme.panel_border};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {theme.button_hover};
        }}
        QPushButton#closeButton:hover {{
            background-color: {theme.close_hover};
        }}
        QPushButton#accentButton {{
            background-color: {theme.accent};
            border: none;
        }}
        QPushButton#accentButton:hover {{
            background-color: {theme.accent_hover};
        }}
        QComboBox {{
            background-color: {theme.input_bg};
            color: {theme.text_primary};
            border: 1px solid {theme.input_border};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QComboBox:focus {{
            border-color: {theme.input_focus_border};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.panel_bg};
            color: {theme.text_primary};
            border: 1px solid {theme.panel_border};
            selection-background-color: {theme.accent};
        }}
        QLineEdit {{
            background-color: {theme.input_bg};
            color: {theme.text_primary};
            border: 1px solid {theme.input_border};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QLineEdit:focus {{
            border-color: {theme.input_focus_border};
        }}
        QSpinBox {{
            background-color: {theme.input_bg};
            color: {theme.text_primary};
            border: 1px solid {theme.input_border};
            border-radius: 4px;
            padding: 6px 8px;
        }}
        QSpinBox:focus {{
            border-color: {theme.input_focus_border};
        }}
        QCheckBox {{
            color: {theme.text_primary};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.input_border};
            border-radius: 3px;
            background-color: {theme.input_bg};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.accent};
            border-color: {theme.accent};
        }}
        QTabWidget::pane {{
            border: 1px solid {theme.panel_border};
            border-radius: 4px;
            background-color: {theme.panel_bg};
        }}
        QTabBar::tab {{
            background-color: {theme.tab_bg};
            color: {theme.text_secondary};
            border: 1px solid {theme.panel_border};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 16px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {theme.tab_selected};
            color: {theme.text_primary};
        }}
        QScrollBar:vertical {{
            background: {theme.scrollbar_bg};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.scrollbar_handle};
            border-radius: 5px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {theme.panel_border};
            height: 6px;
            background: {theme.input_bg};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {theme.accent};
            border: none;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {theme.accent_hover};
        }}
        QDialog {{
            background-color: {theme.panel_bg};
        }}
        QMessageBox {{
            background-color: {theme.panel_bg};
        }}
    """
