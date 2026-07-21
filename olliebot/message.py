from __future__ import annotations

import re
import shlex
from typing import Union

from twitchio.ext import commands
import twitchio

COMMAND_HEADER = re.compile(r"\?[a-zA-Z-]+")


def is_command_header(message_content: str) -> bool:
    return bool(COMMAND_HEADER.fullmatch(message_content))


def get_message(message_or_context: Union[twitchio.ChatMessage, commands.Context]) -> twitchio.ChatMessage:
    if hasattr(message_or_context, "message"):
        return message_or_context.message
    return message_or_context


def get_command_string(
    message_or_context: Union[twitchio.ChatMessage, commands.Context],
    split: bool = False,
    prefix: str = "?",
) -> Union[str, list[str]]:
    message = get_message(message_or_context)
    content = str(message.content).strip()

    if content.startswith(prefix):
        content = content[len(prefix) :].strip()

    if split:
        try:
            return shlex.split(content)
        except ValueError:
            return content.split()

    return content


def get_user(message_or_context: Union[twitchio.ChatMessage, commands.Context]) -> str:
    message = get_message(message_or_context)
    content = str(message.content).strip()
    parts = content.split()

    if parts and is_command_header(parts[0]):
        if len(parts) > 1:
            return parts[1].lstrip("@")
        return message.author.name

    if parts:
        return parts[0].lstrip("@")

    return message.author.name
