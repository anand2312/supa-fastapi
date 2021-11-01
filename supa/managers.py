from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from httpx import AsyncClient
from pgrest import Client as DatabaseClient


class DatabaseClientManager:
    def __init__(self, base_url: str, key: str) -> None:
        self.key = key
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apiKey": key,
            "Authorization": f"Bearer {key}"
        }
        self._client = AsyncClient()
        self._db_client = DatabaseClient(base_url=base_url, headers=self.headers, session=self._client)

    @contextmanager
    def get_client(self, access_token: str) -> Generator[DatabaseClient, None, None]:
        try:
            yield self._db_client.auth(access_token)
        finally:
            self._db_client.auth(self.key)
