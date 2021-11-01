from __future__ import annotations

from typing import Optional
from supa.managers import DatabaseClientManager
from supa.storage import StorageClient

# to support extras, individually suppresss possible import errors
try:
    from pgrest import Client as DatabaseClient
except ImportError:
    DatabaseClient = None
try:
    from realtime import Socket as RealtimeSocket
except ImportError:
    RealtimeSocket = None
try:
    from gotrue import AsyncGoTrueClient
except ImportError:
    AsyncGoTrueClient = None


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

        self._db_manager = DatabaseClientManager(self.rest_url, self.key)

    def storage(self, access_token: Optional[str] = None) -> StorageClient:
        """
        Get the storage client.
        
        Args:
            access_token: The access_token of the currently signed in user.
        Returns:
            [StorageClient][supa.storage.StorageClient]
        """
        return StorageClient(self.storage_url, self._get_headers(access_token))

    def db(self, access_token: Optional[str] = None) -> DatabaseClient:  # type: ignore
        """
        Get the database client, which connects with the provided access_token. If not specified, the anon key is used.

        !!! note
            Data cannot be retrieved with the anon key if RLS is enabled on your tables. But in an authenticated context, it is recommended to use
            [ctx.db][supa.context.Context] instead for database operations, as it will automatically be set with the right access_token.
        
        Args:
            access_token: The access_token of the currently signed in user.
        Returns:
            [DatabaseClient][pgrest.Client]
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apiKey": self.key,
            "Authorization": f"Bearer {access_token or self.key}"
        }
        try:
            client = DatabaseClient(self.rest_url, headers=headers)  # type: ignore
        except TypeError:
            raise ImportError("You have not installed the `db` extra. Install it with \n pip install supa-fastapi[db]")
        else:
            return client

    def _get_headers(self, key: Optional[str] = None) -> dict[str, str]:
        # get auth headers
        return {
            "apiKey": self.key,
            "Authorization": f"Bearer {key or self.key}"
        }
