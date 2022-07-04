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
    ## TODO We could decompose into a CommandString:
    ##      - Command header: str
    ##      - Command name: str = header.removeprefix("?")
    ##      - Command string: list[str]
    ## Could use an argument parser to split the command string into parameter-argument pairs.
    ## Could use something like: command_string: CommandString = self.get_command_string("method_name", context)
    ## where the command string getter is a predefined dictionary from command names to argument parsers for those commands
    ## so that command strings are pre-parsed and have their parameter-argument mappings generated already.
    ## Could we re-wrap command functions to do this?
    message: twitchio.Message = get_message(message_or_context)
    message_string: str = str(message.content)
    
    if message_string.startswith("?") and " " in message_string:
        message_string = message_string.split(" ", 1)[1]
    
    if split:
        return message_string.split(" ")
    return message_string

def is_command_header(message_content: str) -> bool:
    """
    Determine whether a given string is a command header.
    
    A command header is a (possibly hyphenated) alphabetic string prefixed by a question mark.
    """
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