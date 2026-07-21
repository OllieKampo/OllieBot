"""OllieBot package entrypoint."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from .bot import OllieBot

__all__ = ["OllieBot"]


def __getattr__(name: str):
	if name == "OllieBot":
		from .bot import OllieBot

		return OllieBot
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
