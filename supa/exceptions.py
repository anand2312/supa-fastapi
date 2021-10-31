class SupaError(Exception):
    """Base supa-fastapi exception."""


class StorageError(SupaError):
    """Error raised when an operation on the storage API fails."""

