import sqlite3
import argparse
from typing import Literal, Optional
import twitchio
from twitchio.ext import commands
from Core.MessageFunctions import get_command_string, get_message

from Cogs.OllieBotCog import OllieBotCog

__all__ = ("PyramidHandler")

class PyramidHandler(OllieBotCog):
    "Class for handling pyramid attempts."
    
    __slots__ = ("__connection",
                 "__cursor",
                 "__theif",
                 "__destroy",
                 "__timeout",
                 "__last_sender_name",
                 "__pyramid_emote",
                 "__pyramid_progress",
                 "__pyramid_max_height")
    
    def __init__(self) -> None:
        """
        Create a pyramid handler.
        
        Modes
        -----
        `theif` - Attempt to steal pyramids that are about to be completed.
        
        `destroyer` - Destroy pyramids when they reach 3-width.
        
        `timeout` - Timeout failed or incorrect pyramids.
        """
        ## SQL connections
        self.__connection: sqlite3.Connection = sqlite3.connect("SQL/pyramids.sqlite3")
        self.__cursor: sqlite3.Cursor = self.__connection.cursor()
        
        ## Modes
        self.__theif: bool = False
        self.__destroy: bool = False
        self.__timeout: bool = True
        
        ## Pyramid tracking variables
        self.__last_sender_name: str = ""
        self.__pyramid_emote: str = ""
        self.__pyramid_progress: int = 0
        self.__pyramid_max_height: int = 0
    
    @classmethod
    def module_modes() -> dict[str, bool]:
        return {"theif" : False, "destroy" : False, "timeout" : True}
    
    async def handle_pyramids(self, context: commands.Context) -> None:
        "Handle the pyramids for the given chat message, requires echo messages."
        
        message: twitchio.Message = get_message(context)
        split_message: list[str] = str(message.content).split(" ")
        current_sender_name: str = str(context.author.name)
        is_stolen: bool = False
        
        print(f"Before: current pyramider={current_sender_name}, message emote={split_message[0]}, last pyramider={self.__last_sender_name}, current emote={self.__pyramid_emote}, progress={self.__pyramid_progress}")
        
        ## The pyramid has been progressed correctly iff;
        ##      - All the words in the message are the same,
        ##      - The number of messages is one greater or one smaller than the number in the previous level.
        if valid := (all(emote == self.__pyramid_emote
                         for emote in split_message)
                     and ((pyramid_level := len(split_message))
                         in [self.__pyramid_progress + 1,
                             self.__pyramid_progress - 1])):
            
            ## Check whether we are going down or up the pyramid
            on_downwards: bool = pyramid_level == (self.__pyramid_progress - 1)
            on_upwards: bool = not on_downwards
            
            ## Update the progres of the pyramid
            self.__pyramid_max_height = max(self.__pyramid_max_height, pyramid_level)
            self.__pyramid_progress = pyramid_level
            print(f"Pyramid height: current level = {pyramid_level}, max height at = {self.__pyramid_max_height}")
            
            ## Try to destroy the pyramid after level 3
            if self.__destroy and on_upwards and pyramid_level == 3:
                await context.send(f"No {message.author.name} :)")
            
            ## Try to steal the pyramid on the last emote
            if self.__theif and on_downwards and pyramid_level == 2:
                await context.send(f"{self.__pyramid_emote}")
            
            print(f"Success check: direction correct = {on_downwards}, level = {pyramid_level}, max height = {self.__pyramid_max_height}")
            
            ## Declare success if the pyramid is complete
            if (on_downwards and pyramid_level == 1
                and self.__pyramid_max_height >= 3):
                
                ## The pyramid was stolen iff the current sender is not the same as the last
                is_stolen = current_sender_name != self.__last_sender_name
                
                if (self.__pyramid_max_height == 3
                    and not is_stolen
                    and any((user_type in context.author.badges
                             and context.author.badges[user_type] == 1)
                            for user_type in ["vip", "moderator"])):
                    await context.send(f"That doesn't count {current_sender_name} Weirdge")
                    return
                
                ## Declare success
                await self.declare_pyramid(current_sender_name, result="success", stolen=is_stolen, size=self.__pyramid_max_height)
                if current_sender_name != "OllieDoggoBot":
                    total_successes = await self.get_score(current_sender_name, score="success")
                    await context.send(f"OhMyDog Nice pyramid {current_sender_name} POGGERS Thats your {make_ordinal(total_successes)} successful pyramid Radge"
                                       + (f" You stole it from {self.__last_sender_name} PepeLaugh" if is_stolen else ""))
        
        ## This is a failed pyramid iff;
        ##      - It is invalid but has progressed beyond its base size,
        ##      - Or it was stolen.
        if (not valid and self.__pyramid_progress >= 2) or is_stolen:
            await self.declare_pyramid(self.__last_sender_name, result="failed")
            total_failures = await self.get_score(self.__last_sender_name, score="failed")
            
            if self.__timeout:
                if current_sender_name == "OllieDoggoBot":
                    await context.send(f"Get absolutely destroyed {self.__last_sender_name} EZ Clap Thats your {make_ordinal(total_failures)} failed pyramid WeirdChamping See you in 10 peepoHey")
                else: await context.send(f"You tried {self.__last_sender_name}, you failed :) Thats your {make_ordinal(total_failures)} failed pyramid WeirdChamping See you in 10 peepoHey")
                
                ## Timeout the last sender to post a valid level of the pyramid.
                await context.send(f"/timeout {self.__last_sender_name} 600")
            
            else: await context.send(f"Absolute failure {self.__last_sender_name} PogO Thats your {make_ordinal(total_failures)} failed pyramid WeirdChamping")
            
            ## If the pyramid was blocked
            if not is_stolen and current_sender_name != self.__last_sender_name:
                await self.declare_pyramid(current_sender_name, result="blocked")
                total_blocked = await self.get_score(current_sender_name, score="blocked")
                await context.send(f"Nice block {current_sender_name} BASED Thats your {make_ordinal(total_blocked)} blocked pyramid YEP")
        
        ## Reset the pyramid if it is no longer valid (it was not progressed correctly).
        if not valid:
            self.__pyramid_emote = split_message[0]
            self.__pyramid_max_height = 1
            self.__pyramid_progress = 1
        
        ## Keep track to sent the most recent valid level in the pyramid
        self.__last_sender_name = current_sender_name
        
        print(f"After: Current pyramider={self.__last_sender_name}, emote={self.__pyramid_emote}, progress={self.__pyramid_progress}")
    
    async def declare_pyramid(self,
                              chatter_name: str,
                              result: Literal["success", "failed", "blocked"],
                              stolen: bool = False,
                              size: int = 0
                              ) -> None:
        "Declare that a chatter succeeded or failed a pyramid attempt."
        ## Fields are:
        ##      - chatter_name: varchar(255) PRIMARY KEY,
        ##      - success: int,
        ##      - failed: int,
        ##      - blocked: int,
        ##      - stolen: int,
        ##      - biggest: int.
        self.__cursor.execute("""
                              INSERT OR IGNORE INTO pyramid_scores
                              VALUES (:name, 0, 0, 0, 0, 0)
                              """,
                              {"name" : chatter_name})
        self.__cursor.execute(f"""
                              UPDATE pyramid_scores
                              SET {result} = {result} + 1,
                                   stolen = stolen + :stolen,
                                   biggest = MAX(:size, biggest)
                              WHERE chatter_name = :name
                              """,
                              {"stolen" : 1 if stolen else 0,
                               "size" : size,
                               "name" : chatter_name})
        self.__connection.commit()
    
    async def get_score(self,
                        chatter_name: str,
                        score: Literal["success", "failed", "blocked", "stolen"],
                        ) -> Optional[int]:
        self.__cursor.execute(f"""
                              SELECT chatter_name, {score}
                              FROM pyramid_scores
                              WHERE chatter_name = :name
                              """,
                              {"name" : chatter_name})
        result: Optional[tuple[str, int]] = self.__cursor.fetchone()
        if result is not None:
            return result[1]
        return None
    
    async def get_high_scores(self,
                              score: Literal["success", "failed", "blocked", "stolen"],
                              top_scores: int = 4
                              ) -> list[tuple[str, int]]:
        self.__cursor.execute(f"""
                              SELECT *
                              FROM (SELECT chatter_name, {score} FROM pyramid_scores ORDER BY {score} DESC)
                              LIMIT {top_scores}
                              """)
        return self.__cursor.fetchall()
    
    def _get_pyramid_score_args(self, context: commands.Context) -> tuple[str, str]:
        if not hasattr(self, "pyramid_score_parser"):
            
            parser = argparse.ArgumentParser()
            parser.add_argument("score", type=str)
            parser.add_argument("-user", type=str, default=None)
            
            self.pyramid_score_parser = parser
        
        namespace: argparse.Namespace = self.pyramid_score_parser.parse_known_args(get_command_string(context, split=True))[0]
        
        return (namespace.score, namespace.user.lower() if namespace.user is not None else context.author.name)
    
    @commands.command()
    async def pyramid_score(self, context: commands.Context) -> None:
        sender: str = context.author.name
        score_type, user = self._get_pyramid_score_args(context)
        if user.startswith("@"):
            user = user[1:]
        if score_type in ["success", "failed", "blocked", "stolen"]:
            score: Optional[int] = await self.get_score(user, score_type)
            if score is not None:
                if user != sender:
                    await context.send(f"{sender} : {user} has {'completed' if score_type == 'success' else score_type} {score} pyramids.")
                else: await context.send(f"{sender} : You have {'completed' if score_type == 'success' else score_type} {score} pyramids.")
            else: await context.send(f"{sender} : Cannot find user \"{user}\" in database.")
        else: await context.send(f"{sender} : Unkown score type, must be one of; success, failed, blocked, stolen")
    
    @commands.command()
    async def pyramid_high_scores(self, context: commands.Context) -> None:
        sender: str = context.author.name
        score_type, user = self._get_pyramid_score_args(context)
        if score_type in ["success", "failed", "blocked", "stolen"]:
            high_scores: list[tuple[str, int]] = await self.get_high_scores(score_type)
            await context.send(f"{sender} : Current high scores for {'completed' if score_type == 'success' else score_type} pyramids :: "
                               + ", ".join(f"{make_ordinal(i)}: {result[1]} - {result[0]}" for i, result in enumerate(high_scores, start=1)))
        else: await context.send(f"{sender} : Unkown score type, must be one of; success, failed, blocked, stolen")

def make_ordinal(number: int) -> str:
    """
    Convert an integer into its ordinal representation.
    From: https://stackoverflow.com/a/50992575/8344867
    """
    number = int(number)
    if 11 <= (number % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(number % 10, 4)]
    return str(number) + suffix