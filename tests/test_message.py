import pytest

from olliebot.message import get_command_string, get_user


class DummyMessage:
    def __init__(self, content: str, author_name: str = "tester") -> None:
        self.content = content
        self.author = type("Author", (), {"name": author_name})


class DummyContext:
    def __init__(self, content: str, author_name: str = "tester") -> None:
        self.message = DummyMessage(content, author_name)
        self.author = self.message.author


def test_get_command_string_strips_prefix() -> None:
    ctx = DummyContext("?hello world")
    assert get_command_string(ctx) == "hello world"
    assert get_command_string(ctx, split=True) == ["hello", "world"]


def test_get_user_returns_named_user() -> None:
    ctx = DummyContext("?hello somebody")
    assert get_user(ctx) == "somebody"


def test_get_user_defaults_to_author() -> None:
    ctx = DummyContext("?hello")
    assert get_user(ctx) == "tester"
