import pytest


@pytest.fixture(autouse=True)
def fresh_registry():
    import actions
    actions._REGISTRY.clear()
    actions.load_all()
    yield
    actions._REGISTRY.clear()
    actions.load_all()


def test_load_all_registers_builtins():
    import actions
    actions._REGISTRY.clear()
    actions.load_all()
    assert "keyboard" in actions._REGISTRY
    assert "daw" in actions._REGISTRY
    assert "none" in actions._REGISTRY


def test_build_keyboard():
    import actions
    actions.load_all()
    action = actions.build("start", {"action": "keyboard", "keys": [["F5"]]})
    from actions.keyboard import KeyboardAction
    assert isinstance(action, KeyboardAction)
    assert action.name == "start"


def test_build_none_default():
    import actions
    actions.load_all()
    action = actions.build("cancel", {"action": "none"})
    from actions.none import NoneAction
    assert isinstance(action, NoneAction)


def test_build_unknown_raises():
    import actions
    actions.load_all()
    with pytest.raises(ValueError, match="Unknown action type"):
        actions.build("x", {"action": "does_not_exist"})


def test_build_preserves_animation():
    import actions
    actions.load_all()
    action = actions.build("start", {"action": "keyboard", "keys": [["F5"]], "animation": "my_gif"})
    assert action.animation == "my_gif"


def test_load_all_is_idempotent():
    import actions
    actions._REGISTRY.clear()
    actions.load_all()
    first_snapshot = dict(actions._REGISTRY)
    actions.load_all()
    assert actions._REGISTRY == first_snapshot
