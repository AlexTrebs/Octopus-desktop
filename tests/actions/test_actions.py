import pytest


def test_daw_from_config_valid():
    from actions.daw import DawAction
    action = DawAction.from_config("rec", {"action": "daw", "track": "drums", "command": "record"})
    assert action.name == "rec"
    assert action.track == "drums"
    assert action.command == "record"
    assert action.animation is None


def test_daw_from_config_with_animation():
    from actions.daw import DawAction
    action = DawAction.from_config(
        "rec", {"action": "daw", "track": "drums", "command": "record", "animation": "rec_anim"}
    )
    assert action.animation == "rec_anim"


def test_daw_from_config_missing_fields():
    from actions.daw import DawAction
    with pytest.raises(ValueError, match="missing"):
        DawAction.from_config("bad", {"action": "daw", "track": "drums"})


def test_daw_summary():
    from actions.daw import DawAction
    action = DawAction.from_config("rec", {"action": "daw", "track": "drums", "command": "record"})
    assert action.summary() == "[daw] record on drums"


def test_none_from_config():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    assert action.name == "cancel"
    assert action.animation is None


def test_none_from_config_with_animation():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none", "animation": "wave"})
    assert action.animation == "wave"


def test_none_summary():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    assert action.summary() == "[none]"


def test_none_execute_does_not_raise():
    from actions.none import NoneAction
    action = NoneAction.from_config("cancel", {"action": "none"})
    action.execute()
    action.execute(dry_run=True)
