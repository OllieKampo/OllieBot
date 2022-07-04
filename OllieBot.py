import os
import random
import re
import sqlite3
from typing import Union
from twitchio.ext import commands # eventsub, pubsub
import twitchio
from Core.MessageFunctions import get_command_string, get_user

from Cogs.Pyramids import PyramidHandler

class OllieBot(commands.Bot):
    """
    Create an instance of Ollie Bot.
    """
    
    def __init__(self,
                 token: str,
                 client_id: str,
                 initial_channels: Union[str, list[str]]):
        
        _initial_channels: list[str]
        if not isinstance(initial_channels, list):
            _initial_channels = [initial_channels]
        else: _initial_channels = initial_channels
        
        print(f"Connecting to: {_initial_channels}")
        super().__init__(token,
                         client_id=client_id,
                         initial_channels=_initial_channels,
                         nick="DoggieKampo",
                         prefix='?')
        
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
    #### Messages
    
    async def event_message(self, message: twitchio.Message) -> None:
        "Event called when a PRIVMSG is received from Twitch."
        
        ## Ignore all `self messages`
        if message.echo:
            return
        
        context: commands.Context = await self.get_context(message)
        
        await self.__pyramid_handler.handle_pyramids(context)
        
        if re.search("sent love to @?DoggieKampo", str(message.content)) is not None:
            await context.send(f"!love @{str(message.content).split(' ')[0]}")
        
        await self.handle_commands(message)
    
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
    async def treat(self, context: commands.Context) -> None:
        ... ## TODO
    
    @commands.command()
    async def roulette(self, context: commands.Context) -> None:
        "The chatter has a 1 in 6 chance of being timed out for 2 minutes."
        if not random.randint(0, 5):
            await context.send(f"/timeout {context.author.name} 2m")
            await context.send(f"The die is rolled PauseChamp The chatter is lost PepeHands")
        else: await context.send(f"The die is rolled PauseChamp The chatter survives widepeepoHappy")
    
    @commands.command()
    async def high_stakes_roulette(self, context: commands.Context) -> None:
        if not random.randint(0, 1):
            await context.send(f"/timeout {context.author.name} 2m")
            await context.send("I didn't bother rolling the die YEP I decided you lost anyway BigBrother")
        elif not random.randint(0, 5):
            await context.send(f"/timeout {context.author.name} 2m")
            await context.send("The die is rolled PauseChamp The chatter is lost PepeHands")
        else: await context.send("The die is rolled PauseChamp The chatter survives widepeepoHappy")
    
    @commands.command()
    async def low_stakes_roulette(self, context: commands.Context) -> None:
        await context.send(f"/timeout {context.author.name} 2m")
        await context.send(f"Coward {context.author.name} :)")

if __name__ == "__main__":
    connection: sqlite3.Connection = sqlite3.connect("SQL/twitch_channels.sqlite3")
    cursor: sqlite3.Cursor = connection.cursor()
    cursor.execute("""
                   SELECT channel_name
                   FROM channels
                   """)
    channel_list: list[str] = cursor.fetchall()
    connection.close()
    
    ollie_bot = OllieBot(os.getenv("TMI_TOKEN"),
                         os.getenv("CLIENT_ID"),
                         "Froggen")
    ollie_bot.run()

class ChannelJoiner:
    def __init__(self) -> None:
        pass
    
    ## This has to have a socket or something similar that;
    ##      - blocks and waits for a redirect from twitch with an auth token,
    ##      - accepts the connection,
    ##      - obtains the user id (how do we obtain this?) and the auth token,
    ##      - it then saves to the sql database; channel_name, channel_owner_id, join_date, enabled, auth_token, refresh_token, tokens_valid
    ##      - it then calls a join channel method with the given channel name that queries the database again, loads the api tokens to be used by the HTTP "requests" connection for api calls related to that specific channel,
    ##      - this then in turn calls twitchio's join channel method, which connects to the twitch IRC server.