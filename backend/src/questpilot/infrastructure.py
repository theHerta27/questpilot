from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class JsonCache(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None: ...


class MemoryJsonCache:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self.values.get(key)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        self.values[key] = value


class RedisJsonCache:
    def __init__(self, url: str) -> None:
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError("Redis support requires the optional 'redis' package") from exc

        self.client = Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        self.client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))


class ObjectStore(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("object key escapes the configured root")
        return target

    def put(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3ObjectStore:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("S3 support requires the optional 'boto3' package") from exc

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def put(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
