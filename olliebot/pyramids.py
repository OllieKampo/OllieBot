from __future__ import annotations

import argparse
from asyncio import Lock
from typing import TYPE_CHECKING, Optional

import aiosqlite
from twitchio.ext import commands

if TYPE_CHECKING:
    from .bot import OllieBot

VALID_SCORE_COLUMNS = {"success", "failed", "blocked", "stolen"}


class PyramidCog(commands.Component):

    def __init__(self, bot: OllieBot) -> None:
        self.bot = bot
        self.state_lock = Lock()
        self.pyramid_emote = ""
        self.pyramid_progress = 0
        self.pyramid_max_height = 0
        self.last_sender_name = ""

    async def handle_pyramids(self, context: commands.Context["OllieBot"]) -> None:
        message = context.content.strip()
        if not message:
            return

        split_message = message.split()
        if len(split_message) < 1:
            return

        emote = split_message[0]
        if self.pyramid_progress == 0:
            self.pyramid_emote = emote
            self.pyramid_progress = 1
            self.pyramid_max_height = 1
            self.last_sender_name = context.author.name or "unknown"
            return

        async with self.state_lock:
            is_valid = (all(word == self.pyramid_emote for word in split_message)
                        and len(split_message) in {self.pyramid_progress + 1, self.pyramid_progress - 1})
            on_downwards = len(split_message) == self.pyramid_progress - 1

            if is_valid:
                self.pyramid_max_height = max(self.pyramid_max_height, len(split_message))
                self.pyramid_progress = len(split_message)

                if on_downwards and self.pyramid_progress == 1 and self.pyramid_max_height >= 3:
                    author_name = context.author.name or "unknown"
                    is_stolen = author_name != self.last_sender_name
                    await self.declare_pyramid(author_name, "success", stolen=is_stolen, size=self.pyramid_max_height)
                    await context.send(f"Nice pyramid {author_name} POGGERS")
            else:
                if self.pyramid_progress >= 2:
                    await self.declare_pyramid(self.last_sender_name, "failed")
                self.pyramid_emote = emote
                self.pyramid_progress = 1
                self.pyramid_max_height = 1
                self.last_sender_name = context.author.name or "unknown"

    async def declare_pyramid(self, chatter_name: str, result: str, stolen: bool = False, size: int = 0) -> None:
        if result not in VALID_SCORE_COLUMNS:
            raise ValueError("Invalid pyramid result type")

        async with aiosqlite.connect(self.bot.sql_directory / "pyramids.sqlite3") as connection:
            await connection.execute(
                "INSERT OR IGNORE INTO pyramid_scores (chatter_name, success, failed, blocked, stolen, biggest) VALUES (?, 0, 0, 0, 0, 0)",
                (chatter_name,),
            )
            await connection.execute(
                f"UPDATE pyramid_scores SET {result} = {result} + 1, stolen = stolen + ?, biggest = MAX(?, biggest) WHERE chatter_name = ?",
                (1 if stolen else 0, size, chatter_name),
            )
            await connection.commit()

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

        await context.send(
            f"{context.author.name} : {user} has {score} {score_type} pyramids."
        )

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
            f"{i+1}: {score} - {user}" for i, (user, score) in enumerate(high_scores)
        )
        await context.send(
            f"{context.author.name} : Current high scores for {score_type} pyramids :: {formatted}"
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
