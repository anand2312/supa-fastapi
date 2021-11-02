from __future__ import annotations

from typing import TYPE_CHECKING

from supa.storage import StorageClient

if TYPE_CHECKING:
    try:
        from pgrest import Client as DatabaseClient
    except ImportError:
        DatabaseClient = None
