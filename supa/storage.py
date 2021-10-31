from dataclasses import dataclass
from datetime import datetime
from typing import Any, IO, Optional, Union

from httpx import AsyncClient, HTTPError, Response

from supa.exceptions import StorageError

# A lot of this file is based on the storage API implementation from https://github.com/supabase-community/supabase-py

DEFAULT_SEARCH_OPTIONS = {
    "limit": 100,
    "offset": 0,
    "sortBy": {
        "column": "name",
        "order": "asc",
    },
}

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

async def _download_content(client: AsyncClient, fp: str) -> Any:
    r = _handle_response(await client.get(f"/object/authenticated/{fp}"))
    return r.content

@dataclass(frozen=True)
class File:
    """
    Represents a file stored in a storage bucket.
    """
    name: str
    bucket_id: str
    owner: str
    id: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime
    metadata: dict[str, str]

    def __post_init__(self) -> None:
        # created_at and updated_at are returned by the API as ISO timestamps
        # so we convert them to datetime objects
        self.created_at = datetime.fromisoformat(self.created_at)  # type: ignore
        self.updated_at = datetime.fromisoformat(self.updated_at)  # type: ignore
        self.last_accessed_at = datetime.fromisoformat(self.last_accessed_at)  # type: ignore


@dataclass
class Bucket:
    """
    Represents a storage bucket.

    Attributes:
        id: The unique ID of the bucket
        name: The name assigned to the bucket
        owner: The owner of the bucket
        public: Whether the bucket is publicly accessible
        created_at: When the bucket was created at
        updated_at: When the bucket was updated at
    """
    id: str
    name: str
    owner: Optional[str]
    public: bool
    created_at: datetime
    updated_at: datetime
    _client: AsyncClient

    def __post_init__(self) -> None:
        self.created_at = datetime.fromisoformat(self.created_at)  # type: ignore
        self.updated_at = datetime.fromisoformat(self.updated_at)  # type: ignore
    
    def get_public_url(self, path: str) -> str:
        """
        Get the public URL of an object.
        !!! warn:
            This method merely constructs the URL based on the parameters passed. It does not check if the URL actually exists.
        
        Args:
            path: The path of the file.
        Returns:
            Public URL
        """
        return f"{self._client.base_url}/object/public/{path}"
    
    async def create_signed_url(self, path: str, expires_in: int) -> str:
        """
        Generate a pre-signed URL to retrieve an object.
        
        Args:
            path: the file path
            expires_in: number of seconds before the URL expires
        Returns:
            The signed URL.
        """
        r = _handle_response(await self._client.post(f"/object/sign/{self.name}/{path}", json={"expiresIn": str(expires_in)}))
        return r.json()["signedURL"]

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
    
    async def move(self, from_path: str, to_path: str) -> dict[str, str]:
        """
        Move a file in the bucket.
        
        !!! tip:
            This method can also be used to rename a file, by changing the target file name passed as argument `to_path`.
        
        Args:
            from_path: The initial path of the file to be moved.
            to_path: The final location of the file.
        Returns:
            The raw API response.
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Example:
            ```py
            await bucket.move("folder/cat.jpg", "folder/newcat.jpg")
            ```
        """
        json = {
            "bucketId": self.id,
            "sourceKey": from_path,
            "destinationKey": to_path
        }
        r = _handle_response(await self._client.post(f"/object/move", json=json))
        return r.json()

    async def copy(self, file_path: str, target: str) -> dict[str, str]:
        """
        Copy a file in the bucket.
        
        Args:
            file_path: The initial path of the file to be copied
            target: The final location of the copy
        Returns:
            The raw API response.
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Example:
            ```py
            await bucket.copy("folder/cat.jpg", "folder/destination.jpg")
            ```
        """
        json = {
            "bucketId": self.id,
            "sourceKey": file_path,
            "destinationKey": target
        }
        r = _handle_response(await self._client.post(f"/object/move", json=json))
        return r.json()

    async def remove(self, path: str) -> dict[str, str]:
        """
        Remove a file from the bucket.
        
        Args:
            path: The path of the file to be removed.
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Returns:
            The raw API response.
        """
        r = _handle_response(await self._client.delete(f"/object/{self.name}/{path}"))
        return r.json()

    async def bulk_remove(self, paths: list[str]) -> list[File]:
        """
        Remove files from the bucket.
        
        Args:
            paths: Paths of files to be removed.
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Returns:
            List of [File][supa.storage.File] objects that were removed.
        """
        r = _handle_response(await self._client.delete(f"/object/{self.name}", json={"prefixes": paths}))  # type: ignore
        return [File(**i) for i in r.json()]

    async def list(self, path: Optional[str] = None, options: dict = {}) -> list[File]:
        """
        Lists files in the bucket under the specified path.
        
        Args:
            path: The folder path
            options: Search options, including `limit`, `offset`, and `sortBy`.
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Returns:
            The list of [File][supa.storage.File] objects that were found.
        """
        json = {
            "prefix": path or "",
            **DEFAULT_SEARCH_OPTIONS,
            **options
        }
        headers = {**self._client.headers, "Content-Type": "application/json"}
        r = _handle_response(await self._client.post(f"/object/list/{self.name}", json=json, headers=headers))
        return [File(**i) for i in r.json()]

    async def download(self, path: str) -> Any:
        """
        Download a file from the bucket.
        
        Args:
            path: The path of the file to be downloaded eg. `folder/file.png`
        Raises:
            [StorageError][supa.storage.StorageError]
        Returns:
            The contents of the file.
        """
        return await _download_content(self._client, f"{self.name}/{path}")

    async def upload(self, path: str, file: Union[IO[bytes], bytes], cache_control: int = 3600, mime_type: str = "text/plain;charset=UTF-8", upsert: bool = False) -> dict[str, str]:
        """
        Upload a file to the bucket.
        
        !!! note:
            Be sure to pass the right mime-type for your file!
        
        Args:
            path: The path the file should be uploaded to.
            file: The file-like object to be uploaded (like an object returned by the `open` function in 'rb' mode) or bytes.
            cache_control: Cache control
            mime_type: The mime-type of the file
            upsert: Whether to do an upsert (UPDATE if the file already exists, else INSERT)
        Raises:
            [StorageError][supa.exceptions.StorageError]
        Returns:
            The raw API response.
        """
        # the supabase lib sets both Content-Type and contentType headers so..let's do that here as well?
        headers = {**self._client.headers, "cacheControl": cache_control, "contentType": mime_type, "upsert": str(upsert), "Content-Type": mime_type}
        filename = path.rsplit("/", maxsplit=1)[-1]

        files = {
            "file": (filename, file, headers["contentType"])
        }
        
        r = _handle_response(await self._client.post(f"/object/{self.name}/{path}", files=files))
        return r.json()


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
