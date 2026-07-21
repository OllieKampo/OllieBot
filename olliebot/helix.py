from __future__ import annotations

from typing import Any, Optional
import httpx


class TwitchHelixClient:
    BASE_URL = "https://api.twitch.tv/helix"

    def __init__(self, app_token: str, client_id: str, client: Optional[httpx.AsyncClient] = None) -> None:
        self.app_token = app_token
        self.client_id = client_id
        self.client = client if client is not None else httpx.AsyncClient(timeout=10.0)

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        headers.setdefault("Authorization", f"Bearer {self.app_token}")
        headers.setdefault("Client-Id", self.client_id)

        response = await self.client.request(method, f"{self.BASE_URL}{path}", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get_user_by_login(self, login: str) -> dict[str, Any]:
        response = await self.request("GET", "/users", params={"login": login})
        users = response.get("data", [])
        if not users:
            raise LookupError(f"Twitch user not found: {login}")
        return users[0]

    async def timeout_user(self, broadcaster_id: str, moderator_id: str, user_id: str, duration: int, reason: str) -> dict[str, Any]:
        payload = {
            "data": {
                "user_id": user_id,
                "duration": duration,
                "reason": reason,
            }
        }
        return await self.request(
            "POST",
            f"/moderation/bans?broadcaster_id={broadcaster_id}&moderator_id={moderator_id}",
            json=payload,
        )
