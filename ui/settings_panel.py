"""Settings dialog with Audio, Appearance, Behavior, and Advanced tabs."""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QSlider,
    QFormLayout,
    QGroupBox,
    QSizePolicy,
)

from config import Config, Environment, save_config
from event_bridge import AssistantSignals
from themes import Theme, THEMES
from level_meter import LevelMeter

logger = logging.getLogger(__name__)


class SettingsPanel(QDialog):
    """Settings dialog with four tabs."""

    theme_changed = pyqtSignal(str)
    worker_restart_requested = pyqtSignal()

    def __init__(
        self,
        config: Config,
        theme: Theme,
        signals: AssistantSignals,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._config = config
        self._theme = theme
        self._signals = signals
        self._needs_restart = False
        self._test_worker = None

        self.setWindowTitle("Settings")
        self.setMinimumSize(480, 420)
        self.resize(520, 480)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Back button
        top_bar = QHBoxLayout()
        back_btn = QPushButton("\u2190 Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(self.accept)
        top_bar.addWidget(back_btn)
        top_bar.addStretch()

        self._restart_label = QLabel("Restart required")
        self._restart_label.setStyleSheet("color: #EAB308; font-weight: bold;")
        self._restart_label.hide()
        top_bar.addWidget(self._restart_label)

        self._restart_btn = QPushButton("Restart Now")
        self._restart_btn.setObjectName("accentButton")
        self._restart_btn.setFixedWidth(100)
        self._restart_btn.clicked.connect(self._do_restart)
        self._restart_btn.hide()
        top_bar.addWidget(self._restart_btn)

        layout.addLayout(top_bar)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._build_audio_tab(), "Audio")
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        tabs.addTab(self._build_behavior_tab(), "Behavior")
        tabs.addTab(self._build_advanced_tab(), "Advanced")
        layout.addWidget(tabs)

    # -- Audio tab -------------------------------------------------------------

    def _build_audio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Device selection
        device_group = QGroupBox("Input Device")
        device_layout = QVBoxLayout(device_group)

        self._device_combo = QComboBox()
        self._populate_devices()
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self._device_combo)

        # Mic test
        test_row = QHBoxLayout()
        self._test_meter = LevelMeter()
        test_row.addWidget(self._test_meter, stretch=1)
        device_layout.addLayout(test_row)

        # Connect live audio level for testing
        self._signals.audio_level.connect(self._test_meter.set_level)

        layout.addWidget(device_group)

        # Sensitivity
        sens_group = QGroupBox("Sensitivity")
        sens_layout = QFormLayout(sens_group)

        self._sens_slider = QSlider(Qt.Orientation.Horizontal)
        self._sens_slider.setMinimum(0)
        self._sens_slider.setMaximum(2)
        self._sens_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._sens_slider.setTickInterval(1)

        env_map = {Environment.QUIET: 2, Environment.MODERATE: 1, Environment.LOUD: 0}
        self._sens_slider.setValue(env_map.get(self._config.environment, 1))
        self._sens_slider.valueChanged.connect(self._on_sensitivity_changed)

        self._sens_label = QLabel(self._config.environment.value)
        sens_layout.addRow(self._sens_label, self._sens_slider)

        hint = QLabel("Low = loud environments, High = quiet environments")
        hint.setObjectName("secondaryLabel")
        hint.setFont(QFont("", 10))
        sens_layout.addRow(hint)

        layout.addWidget(sens_group)
        layout.addStretch()
        return tab

    def _populate_devices(self) -> None:
        try:
            from audio_devices import create_pyaudio, get_input_devices
            pa = create_pyaudio()
            devices = get_input_devices(pa)
            pa.terminate()

            self._device_list = devices
            current_name = self._config.input_device_name

            for i, dev in enumerate(devices):
                self._device_combo.addItem(dev["description"], dev["index"])
                if dev["description"] == current_name:
                    self._device_combo.setCurrentIndex(i)
        except Exception as e:
            logger.warning("Could not list audio devices: %s", e)
            self._device_list = []

    def _on_device_changed(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._device_list):
            return
        dev = self._device_list[idx]
        self._config.input_device_name = dev["description"]
        save_config(self._config)
        self._mark_restart_needed()

    def _on_sensitivity_changed(self, val: int) -> None:
        env_rmap = {2: Environment.QUIET, 1: Environment.MODERATE, 0: Environment.LOUD}
        env = env_rmap.get(val, Environment.MODERATE)
        self._config.environment = env
        self._sens_label.setText(env.value)
        save_config(self._config)
        self._mark_restart_needed()

    # -- Appearance tab --------------------------------------------------------

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setSpacing(12)

        # Theme selector
        self._theme_combo = QComboBox()
        for name in THEMES:
            self._theme_combo.addItem(name)
        self._theme_combo.setCurrentText(self._config.theme)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addRow("Theme:", self._theme_combo)

        # Overlay position preset
        self._overlay_pos_combo = QComboBox()
        for preset in ("top-right", "top-left", "bottom-right", "bottom-left", "custom"):
            self._overlay_pos_combo.addItem(preset)
        self._overlay_pos_combo.setCurrentText(self._config.overlay_position_preset)
        self._overlay_pos_combo.currentTextChanged.connect(self._on_overlay_preset_changed)
        layout.addRow("Overlay Position:", self._overlay_pos_combo)

        # Custom X/Y
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("X:"))
        self._overlay_x_spin = QSpinBox()
        self._overlay_x_spin.setRange(-1, 9999)
        self._overlay_x_spin.setValue(self._config.overlay_x)
        self._overlay_x_spin.valueChanged.connect(self._on_overlay_pos_changed)
        pos_row.addWidget(self._overlay_x_spin)
        pos_row.addWidget(QLabel("Y:"))
        self._overlay_y_spin = QSpinBox()
        self._overlay_y_spin.setRange(-1, 9999)
        self._overlay_y_spin.setValue(self._config.overlay_y)
        self._overlay_y_spin.valueChanged.connect(self._on_overlay_pos_changed)
        pos_row.addWidget(self._overlay_y_spin)
        layout.addRow("Custom Position:", pos_row)

        return tab

    def _on_theme_changed(self, name: str) -> None:
        self.theme_changed.emit(name)

    def _on_overlay_preset_changed(self, preset: str) -> None:
        self._config.overlay_position_preset = preset
        if preset != "custom":
            self._config.overlay_x = -1
            self._config.overlay_y = -1
            self._overlay_x_spin.setValue(-1)
            self._overlay_y_spin.setValue(-1)
        save_config(self._config)

    def _on_overlay_pos_changed(self) -> None:
        self._config.overlay_x = self._overlay_x_spin.value()
        self._config.overlay_y = self._overlay_y_spin.value()
        if self._config.overlay_x >= 0 and self._config.overlay_y >= 0:
            self._overlay_pos_combo.setCurrentText("custom")
            self._config.overlay_position_preset = "custom"
        save_config(self._config)

    # -- Behavior tab ----------------------------------------------------------

    def _build_behavior_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setSpacing(12)

        # Close behavior
        self._close_combo = QComboBox()
        self._close_combo.addItem("Ask Each Time", "ask")
        self._close_combo.addItem("Minimize to Overlay", "minimize")
        self._close_combo.addItem("Quit", "quit")
        for i in range(self._close_combo.count()):
            if self._close_combo.itemData(i) == self._config.close_behavior:
                self._close_combo.setCurrentIndex(i)
                break
        self._close_combo.currentIndexChanged.connect(self._on_close_behavior_changed)
        layout.addRow("Close Button:", self._close_combo)

        # Wake word
        self._wake_word_edit = QLineEdit(self._config.wake_word)
        self._wake_word_edit.editingFinished.connect(self._on_wake_word_changed)
        layout.addRow("Wake Word:", self._wake_word_edit)

        wake_hint = QLabel("Requires restart to take effect")
        wake_hint.setObjectName("secondaryLabel")
        wake_hint.setFont(QFont("", 10))
        layout.addRow("", wake_hint)

        # Command timeout
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 10)
        self._timeout_spin.setSuffix(" seconds")
        self._timeout_spin.setValue(self._config.command_timeout)
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        layout.addRow("Command Timeout:", self._timeout_spin)

        return tab

    def _on_close_behavior_changed(self, idx: int) -> None:
        val = self._close_combo.itemData(idx)
        if val:
            self._config.close_behavior = val
            save_config(self._config)

    def _on_wake_word_changed(self) -> None:
        new_word = self._wake_word_edit.text().strip().lower()
        if new_word and new_word != self._config.wake_word:
            self._config.wake_word = new_word
            save_config(self._config)
            self._mark_restart_needed()

    def _on_timeout_changed(self, val: int) -> None:
        self._config.command_timeout = val
        save_config(self._config)
        self._mark_restart_needed()

    # -- Advanced tab ----------------------------------------------------------

    def _build_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Warning
        warning = QLabel("\u26A0 Only change these if you know what you're doing")
        warning.setStyleSheet(
            "background-color: rgba(234, 179, 8, 0.15); "
            "border: 1px solid #EAB308; border-radius: 4px; padding: 8px;"
        )
        layout.addWidget(warning)

        form = QFormLayout()
        form.setSpacing(10)

        # Sample rate (read-only)
        form.addRow("Sample Rate:", QLabel("16000 Hz (required by Vosk)"))

        # Detection mode (informational)
        mode = "Porcupine + Vosk" if self._config.use_porcupine else "Vosk"
        form.addRow("Detection Mode:", QLabel(mode))

        # Audio processing checkboxes
        self._audio_processing_cb = QCheckBox("Enable Audio Processing (AGC + Noise Reduction)")
        self._audio_processing_cb.setChecked(self._config.enable_audio_processing)
        self._audio_processing_cb.toggled.connect(self._on_audio_processing_changed)
        form.addRow(self._audio_processing_cb)

        # Debug logging
        self._debug_cb = QCheckBox("Enable Debug Logging")
        self._debug_cb.setChecked(self._config.log_level == "DEBUG")
        self._debug_cb.toggled.connect(self._on_debug_changed)
        form.addRow(self._debug_cb)

        # Porcupine access key (if applicable)
        self._porcupine_key_edit = QLineEdit(self._config.porcupine_access_key)
        self._porcupine_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._porcupine_key_edit.setPlaceholderText("Enter Picovoice access key...")
        self._porcupine_key_edit.editingFinished.connect(self._on_porcupine_key_changed)
        form.addRow("Porcupine Key:", self._porcupine_key_edit)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    def _on_audio_processing_changed(self, checked: bool) -> None:
        self._config.enable_audio_processing = checked
        save_config(self._config)
        self._mark_restart_needed()

    def _on_debug_changed(self, checked: bool) -> None:
        self._config.log_level = "DEBUG" if checked else "INFO"
        save_config(self._config)
        import logging as _logging
        _logging.getLogger().setLevel(
            _logging.DEBUG if checked else _logging.INFO
        )

    def _on_porcupine_key_changed(self) -> None:
        key = self._porcupine_key_edit.text().strip()
        if key != self._config.porcupine_access_key:
            self._config.porcupine_access_key = key
            save_config(self._config)
            self._mark_restart_needed()

    # -- Restart logic ---------------------------------------------------------

    def _mark_restart_needed(self) -> None:
        self._needs_restart = True
        self._restart_label.show()
        self._restart_btn.show()

    def _do_restart(self) -> None:
        self._needs_restart = False
        self._restart_label.hide()
        self._restart_btn.hide()
        self.worker_restart_requested.emit()
