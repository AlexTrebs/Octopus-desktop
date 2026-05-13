"""Tests for Config loading, command parsing, and error handling."""
import json
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    """Isolated Config environment: patches PROJECT_ROOT, stubs load_dotenv, sets env vars."""
    monkeypatch.setattr("config.load_dotenv", lambda path: None)
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)

    monkeypatch.setenv("WAKE_WORD", "octopus")
    monkeypatch.setenv("ENVIRONMENT", "Moderate")
    monkeypatch.setenv("COMMAND_TIMEOUT", "3")
    monkeypatch.setenv("ENABLE_AUDIO_PROCESSING", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("VOSK_MODEL_PATH", "vosk-small")
    monkeypatch.setenv("PORCUPINE_ACCESS_KEY", "")
    monkeypatch.setenv("THEME", "Dark")
    monkeypatch.setenv("OVERLAY_X", "-1")
    monkeypatch.setenv("OVERLAY_Y", "-1")
    monkeypatch.setenv("OVERLAY_POSITION", "top-right")
    monkeypatch.setenv("CLOSE_BEHAVIOR", "ask")

    (tmp_path / "config.env").write_text("")
    (tmp_path / "commands.json").write_text("{}")
    return tmp_path


def _write_commands(tmp_path, data: dict):
    (tmp_path / "commands.json").write_text(json.dumps(data))


# --- Valid loads ---

def test_empty_commands_loads_ok(fake_env):
    from config import Config
    c = Config()
    assert c.commands == {}


def test_keyboard_command_loaded(fake_env):
    _write_commands(fake_env, {"start": {"action": "keyboard", "keys": [["F5"]]}})
    from config import Config
    c = Config()
    assert "start" in c.commands
    assert c.commands["start"].action_type == "keyboard"


def test_animation_field_preserved(fake_env):
    _write_commands(fake_env, {
        "start": {"action": "keyboard", "keys": [["F5"]], "animation": "start_anim"}
    })
    from config import Config
    c = Config()
    assert c.commands["start"].animation == "start_anim"


def test_none_action_loaded(fake_env):
    _write_commands(fake_env, {"cancel": {"action": "none"}})
    from config import Config
    c = Config()
    assert c.commands["cancel"].action_type == "none"


def test_daw_action_loaded(fake_env):
    _write_commands(fake_env, {
        "record drums": {"action": "daw", "track": "drums", "command": "record"}
    })
    from config import Config
    c = Config()
    assert c.commands["record drums"].action_type == "daw"


def test_multiple_commands(fake_env):
    _write_commands(fake_env, {
        "start": {"action": "keyboard", "keys": [["F5"]]},
        "stop": {"action": "keyboard", "keys": [["F6"]]},
        "cancel": {"action": "none"},
    })
    from config import Config
    c = Config()
    assert len(c.commands) == 3
    assert c.command_names() == ["start", "stop", "cancel"]


# --- Errors ---

def test_unknown_action_raises(fake_env):
    _write_commands(fake_env, {"x": {"action": "doesnotexist"}})
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="Unknown action type"):
        Config()


def test_invalid_json_raises(fake_env):
    (fake_env / "commands.json").write_text("{bad json")
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="Invalid JSON"):
        Config()


def test_missing_commands_file_raises(fake_env, monkeypatch):
    monkeypatch.setenv("COMMAND_CONFIG_PATH", "nonexistent.json")
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="Commands file not found"):
        Config()


def test_missing_config_env_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="Configuration file not found"):
        Config()


def test_invalid_environment_raises(fake_env, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "NotAnEnvironment")
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="Invalid ENVIRONMENT"):
        Config()


def test_invalid_timeout_raises(fake_env, monkeypatch):
    monkeypatch.setenv("COMMAND_TIMEOUT", "notanint")
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="COMMAND_TIMEOUT must be an integer"):
        Config()


def test_keyboard_missing_keys_raises(fake_env):
    _write_commands(fake_env, {"start": {"action": "keyboard"}})
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="missing 'keys'"):
        Config()


def test_keyboard_invalid_key_raises(fake_env):
    _write_commands(fake_env, {"start": {"action": "keyboard", "keys": [["NotAKey"]]}})
    from config import Config, ConfigError
    with pytest.raises(ConfigError, match="invalid key"):
        Config()


# --- use_porcupine property ---

def test_use_porcupine_false_without_key(fake_env):
    from config import Config
    c = Config()
    assert c.use_porcupine is False


def test_use_porcupine_false_with_key_but_no_ppn(fake_env, monkeypatch):
    monkeypatch.setenv("PORCUPINE_ACCESS_KEY", "somekey")
    monkeypatch.setenv("PORCUPINE_MODEL_PATH", "missing.ppn")
    from config import Config
    c = Config()
    assert c.use_porcupine is False


def test_use_porcupine_true_with_key_and_ppn(fake_env, monkeypatch, tmp_path):
    (tmp_path / "octopus.ppn").write_bytes(b"")
    monkeypatch.setenv("PORCUPINE_ACCESS_KEY", "somekey")
    monkeypatch.setenv("PORCUPINE_MODEL_PATH", "octopus.ppn")
    from config import Config
    c = Config()
    assert c.use_porcupine is True


# --- print_summary ---

def test_print_summary_runs_without_error(fake_env, capsys):
    _write_commands(fake_env, {"start": {"action": "keyboard", "keys": [["F5"]]}})
    from config import Config
    c = Config()
    c.print_summary()
    captured = capsys.readouterr()
    assert "Wake word" in captured.out
    assert "octopus" in captured.out


def test_print_summary_lists_commands(fake_env, capsys):
    _write_commands(fake_env, {"start": {"action": "keyboard", "keys": [["F5"]]}})
    from config import Config
    c = Config()
    c.print_summary()
    captured = capsys.readouterr()
    assert "start" in captured.out


# --- save_config ---

def test_save_config_writes_wake_word(fake_env, monkeypatch, tmp_path):
    from config import Config, save_config
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    c = Config()
    save_config(c)
    text = (tmp_path / "config.env").read_text()
    assert "WAKE_WORD=octopus" in text


def test_save_config_writes_environment(fake_env, monkeypatch, tmp_path):
    from config import Config, save_config
    monkeypatch.setattr("config.PROJECT_ROOT", tmp_path)
    c = Config()
    save_config(c)
    text = (tmp_path / "config.env").read_text()
    assert "ENVIRONMENT=Moderate" in text
