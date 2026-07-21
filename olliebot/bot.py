from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import httpx
import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from .config import TwitchConfig
from .pyramids import PyramidComponent
from .helix import TwitchHelixClient


class OllieBot(commands.Bot):
    def __init__(self, config: TwitchConfig) -> None:
        self.config = config
        self.sql_directory = config.sql_directory
        self.sql_directory.mkdir(parents=True, exist_ok=True)

        self.helix = TwitchHelixClient(
            app_token=config.app_token,
            client_id=config.client_id,
        )

        self.db_lock = asyncio.Lock()
        self.channel_cache: dict[str, tuple[str | None, str]] = {}

        super().__init__(
            client_id=config.client_id,
            client_secret=config.client_secret,
            bot_id=config.bot_id,
            owner_id=config.owner_id,
            prefix=config.prefix,
        )

        self.pyramid_component = PyramidComponent(self)

    @property
    def sql_path(self) -> Path:
        return self.sql_directory / "twitch_channels.sqlite3"

    async def get_broadcaster_id(self, channel_name: str) -> str:
        cached = self.channel_cache.get(channel_name)
        if cached is not None and cached[1]:
            return cached[1]

        user_data = await self.helix.get_user_by_login(channel_name)
        broadcaster_id = str(user_data["id"])
        internal_channel_id = cached[0] if cached is not None else None
        self.channel_cache[channel_name] = (internal_channel_id, broadcaster_id)
        return broadcaster_id

    async def timeout_user(
        self,
        channel_name: str,
        user_login: str,
        reason: str,
        time_secs: int = 600,
    ) -> bool:
        try:
            broadcaster_id = await self.get_broadcaster_id(channel_name)
            user_data = await self.helix.get_user_by_login(user_login)
            await self.helix.timeout_user(
                broadcaster_id=broadcaster_id,
                moderator_id=self.bot_id,
                user_id=str(user_data["id"]),
                duration=time_secs,
                reason=reason,
            )
            return True
        except (LookupError, httpx.HTTPError, KeyError) as exc:
            print(f"Failed to timeout {user_login} in {channel_name}: {exc}")
            return False

    async def event_ready(self) -> None:
        print(f"Logged in as {self.bot_id}")
        await self._ensure_databases()

    async def setup_hook(self) -> None:
        await self._ensure_databases()
        if self.config.bot_access_token and self.config.bot_refresh_token:
            await self.add_token(self.config.bot_access_token, self.config.bot_refresh_token)
        await self.add_component(self.pyramid_component)
        await self._ensure_channel_subscriptions()

    @property
    def pyramid_sql_path(self) -> Path:
        return self.sql_directory / "pyramids.sqlite3"

    async def _ensure_databases(self) -> None:
        async with aiosqlite.connect(self.sql_path.as_posix()) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    internal_channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcaster_id TEXT NOT NULL,
                    channel_name TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN NOT NULL DEFAULT 1
                )
                """
            )
            await connection.commit()

        async with aiosqlite.connect(self.pyramid_sql_path.as_posix()) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pyramid_scores (
                    chatter_name TEXT PRIMARY KEY,
                    success INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    blocked INTEGER NOT NULL DEFAULT 0,
                    stolen INTEGER NOT NULL DEFAULT 0,
                    biggest INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            await connection.commit()

    async def _ensure_channel_subscriptions(self) -> None:
        for channel_name in self.config.initial_channels:
            user_data = await self.helix.get_user_by_login(channel_name)
            broadcaster_id = str(user_data["id"])

            await self.subscribe_websocket(
                eventsub.ChatMessageSubscription(
                    broadcaster_user_id=broadcaster_id,
                    user_id=self.bot_id,
                )
            )

            async with self.db_lock:
                async with aiosqlite.connect(self.sql_path.as_posix()) as connection:
                    await connection.execute(
                        "INSERT OR IGNORE INTO channels (broadcaster_id, channel_name, enabled) VALUES (?, ?, 1)",
                        (broadcaster_id, channel_name),
                    )
                    await connection.commit()

            self.channel_cache[channel_name] = (None, broadcaster_id)

    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        if payload.chatter and payload.chatter.id == self.bot_id:
            return

        ctx = await self.get_context(payload)
        await self.pyramid_component.handle_pyramids(ctx)

        await self.process_commands(payload)

        if payload.text and "sent love to" in payload.text:
            await ctx.send(f"!love @{ctx.author.name}")

    @commands.command()
    async def hello(self, ctx: commands.Context["OllieBot"]) -> None:
        tokens = ctx.content.strip().split()
        user_name = tokens[0] if tokens else None
        if user_name:
            await ctx.send(f"OhMyDog Herrow {user_name} peepoHey <3")
        else:
            await ctx.send(f"OhMyDog Woof woof Herrow {ctx.author.name} OhMyDog")
