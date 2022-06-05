import re
from time import sleep
from typing import Optional, Union
from urllib.parse import SplitResult
from twitchio.ext import commands
import twitchio

async def multi_send_messages(context: commands.Context,
                              messages: list[str],
                              delay: Optional[float] = None
                              ) -> None:
    for message in messages:
        await context.send(message)
        if delay is not None:
            sleep(delay)

def get_message(message_or_context: Union[twitchio.Message, commands.Context]) -> twitchio.Message:
    if isinstance(message_or_context, commands.Context):
        return message_or_context.message
    return message_or_context

def get_command_string(message_or_context: Union[twitchio.Message, commands.Context],
                             split: bool = False) -> Union[str, list[str]]:
    message: twitchio.Message = get_message(message_or_context)
    message_string: str = str(message.content)
    
    if message_string.startswith("?") and " " in message_string:
        message_string = message_string.split(" ", 1)[1]
    
    if split:
        return message_string.split(" ")
    return message_string

def is_command_header(message_content: str) -> bool:
    return re.fullmatch("\?[a-zA-Z-]+", message_content) is not None

def get_user(message_or_context: Union[twitchio.Message, commands.Context]) -> str:
    "Get the name of the user the message was sent to if the message is non-empty, otherwise get the sender."
    
    message: twitchio.Message = get_message(message_or_context)
    split_message: list[str] = str(message.content).split(" ")
    
    if is_command_header(split_message[0]):
        if len(split_message) == 1:
            return message.author.name
        else: return split_message[1]
    if len(split_message) == 0:
        return message.author.name
    else: return split_message[0]