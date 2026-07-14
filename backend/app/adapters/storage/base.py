from __future__ import annotations

from typing import BinaryIO, Protocol


class StorageAdapter(Protocol):
    """Swappable object-storage interface (N5). Same code path for MinIO (local) and S3 (prod)."""

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None: ...

    def presigned_get_url(self, key: str, expires_in: int) -> str: ...

    def open_stream(self, key: str) -> tuple[BinaryIO, str]:
        """Returns (body-stream, content_type) for streaming a download through the API."""
        ...

    def ensure_bucket(self) -> None: ...
