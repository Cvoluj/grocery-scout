import asyncio
import json
import logging
import os

from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class RuntimeSettings:
    def __init__(self):
        self._data: dict = {}

    def load(self, settings: dict):
        self._data = settings

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> str:
        return self._data[key]
runtime = RuntimeSettings()


class PocketBaseClient:
    URL = os.environ["PB_URL"].rstrip("/")
    EMAIL = os.environ["PB_ADMIN_EMAIL"]
    PASSWORD = os.environ["PB_ADMIN_PASSWORD"]

    def __init__(self):
        self._token: str | None = None
        self._session = AsyncSession()

    async def auth(self):
        r = await self._session.post(
            f"{self.URL}/api/collections/_superusers/auth-with-password",
            json={"identity": self.EMAIL, "password": self.PASSWORD},
        )
        self._token = r.json()["token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def get_settings(self) -> dict:
        r = await self._session.get(
            f"{self.URL}/api/collections/settings/records",
            headers=self._headers(),
            params={"perPage": 500},
        )
        return {item["key"]: item["value"] for item in r.json()["items"]}

    async def get_enabled_brands(self) -> list[str]:
        r = await self._session.get(
            f"{self.URL}/api/collections/brands/records",
            headers=self._headers(),
            params={"filter": "enabled=true", "perPage": 500},
        )
        return [item["name"] for item in r.json()["items"]]

    async def subscribe(self):
        client_id: str | None = None
        current_event: str | None = None

        async with self._session.stream(
            "GET",
            f"{self.URL}/api/realtime",
            headers=self._headers(),
        ) as response:
            async for line in response.aiter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")

                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    continue

                if not line.startswith("data:"):
                    continue

                data = json.loads(line[5:].strip())

                if not client_id and "clientId" in data:
                    client_id = data["clientId"]
                    await self._session.post(
                        f"{self.URL}/api/realtime",
                        headers=self._headers(),
                        json={
                            "clientId": client_id,
                            "subscriptions": ["settings", "brands"],
                        },
                    )
                    logger.info("Subscribed, clientId=%s", client_id)
                    continue

                if current_event == "settings":
                    record = data["record"]
                    runtime._data[record["key"]] = record["value"]
                    logger.info("Updated %s=%s", record["key"], record["value"])

                elif current_event == "brands":
                    record = data["record"]
                    logger.info("Brand %s enabled=%s", record.get("name"), record.get("enabled"))


async def start_pb() -> RuntimeSettings:
    pb = PocketBaseClient()
    await pb.auth()
    settings = await pb.get_settings()
    runtime.load(settings)

    async def _realtime_loop():
        while True:
            try:
                await pb.subscribe()
            except Exception as e:
                logger.warning("Realtime reconnecting: %s", e)
                await asyncio.sleep(5)

    asyncio.create_task(_realtime_loop())
    return runtime


if __name__ == "__main__":
    async def main():
        await start_pb()

        async def printer():
            while True:
                print(runtime._data)
                await asyncio.sleep(1)

        await printer()

    asyncio.run(main())
