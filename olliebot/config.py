from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import find_dotenv, load_dotenv

@lru_cache(maxsize=1)
def _load_dotenv() -> None:
    load_dotenv(find_dotenv())


@dataclass(frozen=True)
class TwitchConfig:
    client_id: str
    client_secret: str
    bot_id: str
    owner_id: str
    app_token: str
    initial_channels: tuple[str, ...]
    bot_access_token: str | None = None
    bot_refresh_token: str | None = None
    bot_name: str = "DoggieKampo"
    prefix: str = "?"
    sql_directory: Path = Path("SQL")

    @classmethod
    def from_env(cls) -> "TwitchConfig":
        _load_dotenv()

        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        bot_id = os.getenv("BOT_ID")
        owner_id = os.getenv("OWNER_ID")
        app_token = os.getenv("APP_TOKEN")
        bot_access_token = os.getenv("BOT_ACCESS_TOKEN")
        bot_refresh_token = os.getenv("BOT_REFRESH_TOKEN")
        if not client_id or not client_secret or not bot_id or not owner_id or not app_token:
            raise EnvironmentError(
                "Missing required Twitch environment variables: CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, and APP_TOKEN."
            )

        initial_channels = tuple(
            filter(bool, (os.getenv("TWITCH_CHANNELS", "").split(",")))
        )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            owner_id=owner_id,
            app_token=app_token,
            bot_access_token=bot_access_token,
            bot_refresh_token=bot_refresh_token,
            initial_channels=initial_channels,
        )
