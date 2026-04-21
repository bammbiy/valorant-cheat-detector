import httpx
from fastapi import HTTPException

from backend.core.config import get_settings

cfg = get_settings()


class RiotClient:
    def __init__(self):
        self._headers = {"X-Riot-Token": cfg.riot_api_key}
        self._timeout = cfg.http_timeout

    async def _get(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(url, headers=self._headers)

        if r.status_code == 404:
            raise HTTPException(404, "플레이어를 찾을 수 없습니다.")
        if r.status_code == 403:
            raise HTTPException(403, "API 키가 만료되었거나 유효하지 않습니다.")
        if r.status_code == 429:
            raise HTTPException(429, "API 요청 한도 초과. 잠시 후 다시 시도하세요.")
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Riot API 오류 ({r.status_code})")

        return r.json()

    async def get_account(self, name: str, tag: str, routing: str) -> dict:
        url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        return await self._get(url)

    async def get_match_list(self, puuid: str, platform: str, limit: int = 20) -> list[str]:
        url = f"https://{platform}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
        data = await self._get(url)
        history = data.get("history", [])
        return [m["matchId"] for m in history[:limit]]

    async def get_match(self, match_id: str, platform: str) -> dict:
        url = f"https://{platform}.api.riotgames.com/val/match/v1/matches/{match_id}"
        return await self._get(url)
