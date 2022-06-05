from collections import defaultdict, deque
import os
import random
import re
from time import sleep
from typing import Callable, Coroutine, List, Optional, Union
from twitchio.ext import commands # eventsub, pubsub
import twitchio
from Core.MessageFunctions import get_command_string, get_user

from Cogs.Pyramids import PyramidHandler

# a = eventsub.EventSubClient()
# a.subscribe_channel_points_redeemed()

# twitchio.CustomReward
# twitchio.CustomRewardRedemption

# u = twitchio.User()
# u.get_custom_rewards()

class OllieBot(commands.Bot):
    """
    Create an instance of Ollie Bot.
    """
    
    def __init__(self,
                 token: str,
                 client_id: str,
                 initial_channels: Union[str, List[str]]):
        
        _initial_channels: List[str]
        if not isinstance(initial_channels, list):
            _initial_channels = [initial_channels]
        else: _initial_channels = initial_channels
        
        print(f"Connecting to: {_initial_channels}")
        super().__init__(token,
                         client_id=client_id,
                         initial_channels=_initial_channels,
                         nick="OllieDoggoBot",
                         prefix='?')
        
        # live_chat_logs: dict[str, deque[str]] ## Maps: chatter name -> list of chat messages
        
        self.__modes: dict[str, bool] = defaultdict(lambda: False)
        
        self.__pyramid_handler = PyramidHandler()
        self.add_cog(self.__pyramid_handler)
    
    ##################################################################################
    #### User joining and parting
    
    async def event_join(self, channel: twitchio.Channel, user: twitchio.User):
        "Event called when a JOIN is received from Twitch."
        return await super().event_join(channel, user)
    
    async def event_part(self, user: twitchio.User):
        "Event called when a PART is received from Twitch."
        return await super().event_part(user)
    
    ##################################################################################
    #### Module modes and variables
    
    async def set_mode(self, mode: str) -> bool:
        "Set the given mode to be enabled if it was disabled, and disabled if it was enabled."
        self.__modes[mode] = not self.__modes[mode]
        return self.__modes[mode]
    
    async def is_valid_mode(self, mode: str) -> bool:
        return mode in ["echo", "pyramidtheif", "pyramiddestroyer", "timeout-failed-pyramid"]
    
    ## ?set variables failed_pyramid_timeout_length={"base" : 600, "grow_by" : 5.0}
    ## ?set variables failed_pyramid_accumulation_reset="24h"
    
    ##################################################################################
    #### Messages
    
    async def event_message(self, message: twitchio.Message) -> None:
        "Event called when a PRIVMSG is received from Twitch."
        ## Log to a rotating file handler keeping below 100MB, every time 10 log files are full, 7zip them.
        # print(f"Message from {message.author.name}: {message.content}, {message.tags=}")
        
        ## Ignore all `self messages`
        if message.echo:
            return
        
        context: commands.Context = await self.get_context(message)
        
        await self.__pyramid_handler.handle_pyramids(context)
        
        if re.search("sent love to @?OllieDoggoBot", str(message.content)) is not None:
            await context.send(f"!love @{str(message.content).split(' ')[0]}")
        
        await self.handle_commands(message)
    
    async def event_usernotice_subscription(self, metadata):
        "Event called when a USERNOTICE subscription or re-subscription event is received from Twitch."
        return await super().event_usernotice_subscription(metadata)
    
    ##################################################################################
    #### Raw data
    
    async def event_raw_usernotice(self, channel: twitchio.Channel, tags: dict):
        "Event called when a USERNOTICE is received from Twitch."
        return await super().event_raw_usernotice(channel, tags)
    
    async def event_raw_data(self, data: str):
        pass # print(f"Raw data received: {data!s}")
    
    ##################################################################################
    #### ????
    
    async def event_mode(self, channel: twitchio.Channel, user: twitchio.User, status: str):
        pass # print(f"Event mode: {channel=}, {user=}, {status=}")
    
    async def event_userstate(self, user: twitchio.User):
        pass # print(f"Event user state: {user=}")
    
    ##################################################################################
    #### Built-in commands
    
    @commands.command()
    async def spam(self, context: commands.Context) -> None:
        if context.author.is_mod:
            command_string: str = get_command_string(context)
            for _ in range(10):
                await context.send(command_string)
    
    @commands.command()
    async def hello(self, context: commands.Context) -> None:
        "Greet the user the message was sent to if the message is non-empty, otherwise say hello to the sender."
        user_name: str = get_user(context)
        if user_name != str(context.author.name):
            await context.send(f"OhMyDog Herrow {user_name} peepoHey <3")
        else: await context.send(f"OhMyDog Woof woof Herrow {user_name} OhMyDog")
    
    @commands.command()
    async def roulette(self, context: commands.Context) -> None:
        "The chatter has a 1 in 6 chance of being timed out for 2 minutes."
        if not random.randint(0, 5):
            await context.send(f"/timeout {context.author.name} 2m")
            await context.send(f"The die is rolled PauseChamp The chatter is lost PepeHands")
        else: await context.send(f"The die is rolled PauseChamp The chatter survives widepeepoHappy")
    
    @commands.command()
    async def mode(self, context: commands.Context) -> None:
        "Enable or disable certain operating modes of the bot."
        if context.author.is_mod:
            _command: str = str(context.message.content).lower().removeprefix("?mode ")
            if await self.is_valid_mode(_command):
                enabled: bool = await self.set_mode(_command)
                await context.send(f"{context.author.name}: {_command} mode was "
                                   + ("enabled" if enabled else "disabled"))
            else: await context.send(f"{context.author.name}: {_command} mode is not recognised")

if __name__ == "__main__":
    ollie_bot = OllieBot(os.getenv('TMI_TOKEN'),
                         os.getenv('CLIENT_ID'),
                         "Froggen")
    ollie_bot.run()