from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from httpx import AsyncClient, HTTPError, Response

from supa.exceptions import StorageError


# A lot of this file is based on the storage API implementation from https://github.com/supabase-community/supabase-py

def _handle_response(r: Response) -> Response:
    try:
        r.raise_for_status()
    except HTTPError:
        raise StorageError(r.json())
    else:
        return r


async def _delete_bucket(client: AsyncClient, id: str) -> dict[str, str]:
    r = _handle_response(await client.delete(f"/bucket/{id}"))
    return r.json()


async def _empty_bucket(client: AsyncClient, id: str) -> dict[str, str]:
    r = _handle_response(await client.post(f"/bucket/{id}/empty", json={}))
    return r.json()


@dataclass
class Bucket:
    id: str
    name: str
    owner: Optional[str]
    public: bool
    created_at: datetime
    updated_at: datetime
    _client: AsyncClient

    def __post_init__(self) -> None:
        # created_at and updated_at are returned by the API as ISO timestamps
        # so we convert them to datetime objects
        self.created_at = datetime.fromisoformat(self.created_at)  # type: ignore
        self.updated_at = datetime.fromisoformat(self.updated_at)  # type: ignore
    
    async def delete(self) -> dict[str, str]:
        """
        Delete the bucket.
        !!! note:
            The bucket needs to be emptied before deleting.
        
        Returns:
            The raw API response.
        """
        return await _delete_bucket(self._client, self.id)

    async def empty(self) -> dict[str, str]:
        """
        Empty the bucket.

        Returns:
            The raw API response.
        """
        return await _empty_bucket(self._client, self.id)


class StorageClient:
    """Handles storage functions."""

    def __init__(self, url: str, headers: dict[str, Any]) -> None:
        self.url = url
        self._client = AsyncClient(base_url=self.url, headers=headers)

    async def list_buckets(self) -> list[Bucket]:
        """
        Retrieves all the buckets associated with this project.
        
        Returns:
            [`Optional[list[Bucket]]`][supa.storage.Bucket]
        """
        r = _handle_response(await self._client.get("/bucket"))
        data = r.json()
        return [Bucket(**i, _client=self._client) for i in data]

    async def get_bucket(self, id: str) -> Bucket:
        """
        Retrieves the details of an existing storage bucket.

        Args:
            id: The unique ID of the bucket.
        Returns:
            [Bucket][supa.storage.Bucket]
        """
        r = _handle_response(await self._client.get(f"/bucket/{id}"))
        data = r.json()
        return Bucket(**data, _client=self._client)

    async def create_bucket(self, id: str, *, name: Optional[str] = None, public: bool = False) -> Bucket:
        """
        Create a new storage bucket.
        
        Args:
            id: The unique identifier for the bucket
            name: The name of the bucket. If not specified, the id is used as the name.
            public: Whether the bucket should be publically accessible

        Returns:
            The [Bucket][supa.storage.Bucket] that was created.
            !!! note:
                The bucket returned will have the owner field set to None.
        """
        r = _handle_response(await self._client.post(f"/bucket", json={"id": id, "name": name or id, "public": public}))
        now = datetime.now()
        return Bucket(id=id, name=name or id, owner=None, public=public, created_at=now, updated_at=now, _client=self._client)
    
    async def empty_bucket(self, id: str) -> dict[str, str]:
        """
        Empties the specified bucket.
        
        Args:
            id: The ID of the bucket to empty.
        Returns:
            The raw API response.
        """
        return await _empty_bucket(self._client, id)

    async def delete_bucket(self, id: str) -> dict[str, str]:
        """
        Delete a storage bucket.
        !!! note:
            The bucket needs to be emptied before deleting.

        Args:
            id: The ID of the bucket to delete.
        Returns:
            The raw API response.
        """
        return await _delete_bucket(self._client, id)
