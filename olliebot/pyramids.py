from __future__ import annotations

import argparse
from asyncio import Lock
from typing import TYPE_CHECKING, Optional

import aiosqlite
from twitchio import Chatter
from twitchio.ext import commands

if TYPE_CHECKING:
    from .bot import OllieBot

VALID_SCORE_COLUMNS = {"success", "failed", "blocked", "stolen"}


class PyramidComponent(commands.Component):

    def __init__(self, bot: OllieBot) -> None:
        self.bot: OllieBot = bot
        self.state_lock: Lock = Lock()
        self.pyramid_emote: str = ""
        self.pyramid_progress: int = 0
        self.pyramid_max_height: int = 0
        self.last_sender_name: str = ""

    async def handle_pyramids(self, context: commands.Context["OllieBot"]) -> None:
        author_name: str = context.author.name if context.author.name is not None else "unknown"
        message: str = context.content.strip()
        if not message:
            return
        split_message: list[str] = message.split()
        if len(split_message) < 1:
            return
        emote: str = split_message[0]

        # First time we've got a message, initialize the pyramid state.
        if self.pyramid_progress == 0:
            self.pyramid_emote = emote
            self.pyramid_progress = 1
            self.pyramid_max_height = 1
            self.last_sender_name = author_name
            return

        async with self.state_lock:
            # The pyramid has been progressed correctly iff;
            #      - All the words in the message are the same,
            #      - The number of messages is one greater or one smaller than the number in the previous level.
            pyramid_level: int = len(split_message)
            is_valid: bool = (all(word == self.pyramid_emote for word in split_message)
                        and pyramid_level in {self.pyramid_progress + 1, self.pyramid_progress - 1})
            # The pyramid was stolen iff the current sender is not the same as the last.
            is_stolen: bool = author_name != self.last_sender_name
            # Check whether we are going down or up the pyramid.
            on_downwards: bool = pyramid_level == self.pyramid_progress - 1

            if is_valid:
                # If valid, update the progress of the pyramid.
                self.pyramid_max_height = max(self.pyramid_max_height, pyramid_level)
                self.pyramid_progress = pyramid_level

                # A complete pyramid has been made if we are on the downwards slope and the progress is 1, i.e. we have reached
                # the bottom of the pyramid again, and the pyramid is at least 3 levels high.
                if on_downwards and self.pyramid_progress == 1 and self.pyramid_max_height >= 3:

                    # Mods and VIPs need to make pyramids of height 4 or more because they can send messages faster than normal users.
                    if isinstance(context.author, Chatter) and (context.author.moderator or context.author.vip) and self.pyramid_max_height <= 3 and not is_stolen:
                        await context.send(f"{author_name} : You can't make a pyramid of height 3 or less as a mod or VIP Weirdge")
                        return

                    await self.declare_pyramid(author_name, "success", stolen=is_stolen, size=self.pyramid_max_height)

                    total_successes: int | None = await self.get_score(author_name, score="success")
                    message: str = f"OhMyDog Nice pyramid {author_name}"
                    if total_successes is not None:
                        message += f"POGGERS Thats your {make_ordinal(total_successes)} successful pyramid Radge"
                    if is_stolen:
                        message += f" You stole it from {self.last_sender_name} PepeLaugh" if is_stolen else ""
                    await context.send(message)

            # This is a failed pyramid iff;
            #      - It is invalid but has progressed beyond its base size,
            #      - Or it was stolen.
            if (not is_valid and self.pyramid_progress >= 2) or is_stolen:
                await self.declare_pyramid(self.last_sender_name, "failed")
                total_failures: int | None = await self.get_score(self.last_sender_name, score="failed")
                message: str = f"You tried {self.last_sender_name}, you failed, and we all saw it PepeLaugh"
                if total_failures is not None:
                    message += f" Thats your {make_ordinal(total_failures)} failed pyramid WeirdChamping See you in 5 peepoHey"
                await context.send(message)

                channel_name: str | None = context.channel.name
                if channel_name is not None:
                    await self.bot.timeout_user(channel_name, self.last_sender_name, "Failed pyramid", time_secs=300)

                # If the pyramid was blocked.
                if not is_stolen and author_name != self.last_sender_name:
                    await self.declare_pyramid(author_name, result="blocked")
                    total_blocked: int | None = await self.get_score(author_name, score="blocked")
                    message: str = f"Nice block {author_name} BASED"
                    if total_blocked is not None:
                        message += f" Thats your {make_ordinal(total_blocked)} blocked pyramid YEP"
                    await context.send(message)

            if not is_valid:
                self.pyramid_emote = emote
                self.pyramid_progress = 1
                self.pyramid_max_height = 1

            self.last_sender_name = author_name

    async def declare_pyramid(self, chatter_name: str, result: str, stolen: bool = False, size: int = 0) -> None:
        if result not in VALID_SCORE_COLUMNS:
            raise ValueError("Invalid pyramid result type")

        async with aiosqlite.connect(self.bot.sql_directory / "pyramids.sqlite3") as connection:
            await connection.execute(
                """
                INSERT OR IGNORE INTO pyramid_scores
                (chatter_name, success, failed, blocked, stolen, biggest)
                VALUES (?, 0, 0, 0, 0, 0)
                """,
                (chatter_name,),
            )
            await connection.execute(
                f"""
                UPDATE pyramid_scores
                SET {result} = {result} + 1,
                    stolen = stolen + ?,
                    biggest = MAX(?, biggest)
                WHERE chatter_name = ?
                """,
                (1 if stolen else 0, size, chatter_name),
            )
            await connection.commit()

    async def get_score(self, chatter_name: str, score: str) -> Optional[int]:
        async with aiosqlite.connect(self.bot.sql_directory / "pyramids.sqlite3") as connection:
            cursor = await connection.execute(
                f"SELECT {score} FROM pyramid_scores WHERE chatter_name = ?",
                (chatter_name,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return row[0]

    async def get_high_scores(self, score: str, top_scores: int = 4) -> list[tuple[str, int]]:
        async with aiosqlite.connect(self.bot.sql_directory / "pyramids.sqlite3") as connection:
            cursor = await connection.execute(
                f"SELECT chatter_name, {score} FROM pyramid_scores ORDER BY {score} DESC LIMIT ?",
                (top_scores,),
            )
            rows = await cursor.fetchall()

        return [(str(row[0]), int(row[1])) for row in rows]

    @commands.command(aliases=["pyscore", "ps"])
    async def pyramid_score(self, context: commands.Context["OllieBot"]) -> None:
        score_type, user = self._get_pyramid_score_args(context)
        if score_type is None:
            await context.send(
                f"{context.author.name} : Unknown score type, must be one of; success (s), failed (f), blocked (b), stolen (t)"
            )
            return

        score = await self.get_score(user, score_type)
        if score is None:
            await context.send(f"{context.author.name} : Cannot find user \"{user}\" in the database.")
            return

        sender: str = context.author.name if context.author.name is not None else "unknown"
        if user != sender:
            await context.send(f"{sender} : {user} has {'completed' if score_type == 'success' else score_type} {score} pyramids.")
        else:
            await context.send(f"{sender} : You have {'completed' if score_type == 'success' else score_type} {score} pyramids.")

    @commands.command(aliases=["pyhighscores", "phs"])
    async def pyramid_high_scores(self, context: commands.Context["OllieBot"]) -> None:
        score_type, _ = self._get_pyramid_score_args(context)
        if score_type is None:
            await context.send(
                f"{context.author.name} : Unknown score type, must be one of; success (s), failed (f), blocked (b), stolen (t)"
            )
            return

        high_scores = await self.get_high_scores(score_type)
        formatted = ", ".join(
            f"{make_ordinal(i)}: {score} - {user}" for i, (user, score) in enumerate(high_scores, start=1)
        )
        await context.send(
            f"{context.author.name} : Current high scores for {'completed' if score_type == 'success' else score_type} pyramids :: {formatted}"
        )

    @commands.command()
    async def add_pyramid(self, context: commands.Context["OllieBot"]) -> None:
        author_name = (context.author.name or "").lower()
        is_moderator = bool(getattr(context.chatter, "moderator", False))
        if not is_moderator or author_name != "olliekampo":
            await context.send("Only the bot operator can add pyramid scores.")
            return

        try:
            score_type, user = self._get_pyramid_score_args(context, user_optional=False)
        except ValueError:
            await context.send("You must specify a user to declare a pyramid.")
            return

        if score_type is None:
            await context.send("Unknown score type, must be one of: success, failed, blocked, stolen.")
            return

        await self.declare_pyramid(user, score_type)
        await context.send(f"Declared pyramid as '{score_type}' for {user}.")

    def _get_pyramid_score_args(self, context: commands.Context["OllieBot"], user_optional: bool = True) -> tuple[Optional[str], str]:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("score", type=str)
        parser.add_argument("-user", type=str, default=None)

        args = context.content.strip().split()
        namespace, _ = parser.parse_known_args(args)

        user = namespace.user
        if user is None:
            if user_optional:
                user = context.author.name or "unknown"
            else:
                raise ValueError("User is required.")

        user = user.lstrip("@").lower()
        score = namespace.score.lower()
        if score not in ["success", "failed", "blocked", "stolen"]:
            score = {"s": "success", "f": "failed", "b": "blocked", "t": "stolen"}.get(score)

        return score, user

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
