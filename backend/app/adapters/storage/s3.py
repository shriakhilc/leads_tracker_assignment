from __future__ import annotations

import logging
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageAdapter:
    """S3-compatible storage. Works against AWS S3 (prod) and MinIO (local) unchanged."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if settings.s3_use_path_style else "auto"},
            ),
        )
        self._bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            logger.info("Creating object-storage bucket", extra={"extra": {"bucket": self._bucket}})
            self._client.create_bucket(Bucket=self._bucket)

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self._client.upload_fileobj(
            fileobj, self._bucket, key, ExtraArgs={"ContentType": content_type}
        )

    def presigned_get_url(self, key: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def open_stream(self, key: str) -> tuple[BinaryIO, str]:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"], obj.get("ContentType", "application/octet-stream")


@lru_cache
def get_storage() -> S3StorageAdapter:
    return S3StorageAdapter()
