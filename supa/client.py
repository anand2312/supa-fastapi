from contextlib import suppress
from typing import Optional

from supa.storage import StorageClient

# to support extras, individually suppresss possible import errors
with suppress(ImportError):
    from pgrest import Client
with suppress(ImportError):
    from realtime import Socket
with suppress(ImportError):
    from gotrue import AsyncGoTrueClient


class Supa:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        """
        Initialize the client.

        Args:
            supabase_url: supabase API base URL
            supabase_key: your anon key
        """
        self.url = supabase_url
        self.key = supabase_key

        self.rest_url = f"{self.url}/rest/v1"
        self.realtime_url = f"{self.url}/realtime/v1".replace("http", "ws")
        self.auth_url = f"{self.url}/auth/v1"
        self.storage_url = f"{self.url}/storage/v1"

    def storage(self, access_token: Optional[str] = None) -> StorageClient:
        """
        Get the storage client.
        
        Args:
            access_token: The access_token of the currently signed in user.
        Returns:
            [StorageClient][supa.storage.StorageClient]
        """
        return StorageClient(self.storage_url, self._get_headers(access_token))

    def _get_headers(self, key: Optional[str] = None) -> dict[str, str]:
        # get auth headers
        return {
            "apiKey": self.key,
            "Authorization": f"Bearer {key or self.key}"
        }
