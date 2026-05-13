import pytest
from actions.base import Action


def test_action_is_abstract():
    with pytest.raises(TypeError):
        Action(name="test")


def test_concrete_action_requires_execute():
    class NoExecute(Action):
        action_type = "test"
        def from_config(cls, name, data): ...
        def summary(self): return ""

    with pytest.raises(TypeError):
        NoExecute(name="test")
