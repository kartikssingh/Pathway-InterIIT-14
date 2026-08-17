"""S3 upload helper for KYC form submissions.

The module used to end with ``s3_service = S3Service()``, which built a boto3
client at import time. That made ``import app.routes.user_routes`` require boto3
and AWS credentials even for requests that never touch S3, and a
misconfiguration surfaced as an import error rather than a 503 on one endpoint.

The client is now built on first use and its absence is reported as a clean
:class:`~app.core.errors.UpstreamError`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.errors import UpstreamError
from app.core.logging import get_logger

__all__ = ["S3Service", "s3_service"]

log = get_logger("api.s3")


@dataclass
class UploadResult:
    bucket: str
    key: str
    url: str
    size: int
    etag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket,
            "key": self.key,
            "url": self.url,
            "size": self.size,
            "etag": self.etag,
        }


class S3Service:
    """Thin wrapper over ``boto3`` with lazy client creation."""

    def __init__(self) -> None:
        self._client: Any | None = None
        self._lock = threading.Lock()

    # -- client ------------------------------------------------------------ #

    @property
    def configured(self) -> bool:
        return get_settings().s3.configured

    def _get_client(self) -> Any:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    settings = get_settings().s3
                    if not settings.configured:
                        raise UpstreamError(
                            "File uploads are not configured. Set AWS_S3_BUCKET, "
                            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
                            details={"missing": "aws credentials or bucket"},
                        )
                    try:
                        import boto3
                        from botocore.config import Config
                    except ImportError as exc:
                        raise UpstreamError(f"boto3 is not installed: {exc}") from exc

                    import os

                    self._client = boto3.client(
                        "s3",
                        aws_access_key_id=settings.access_key_id,
                        aws_secret_access_key=settings.secret_access_key,
                        region_name=settings.region,
                        config=Config(
                            s3={
                                "addressing_style": os.getenv("S3_ADDRESSING_STYLE", "virtual")
                            },
                            retries={"max_attempts": 3, "mode": "standard"},
                        ),
                    )
                    log.info("S3 client ready", extra={"bucket": settings.bucket})
        return self._client

    # -- operations -------------------------------------------------------- #

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        *,
        bucket: str | None = None,
        content_type: str | None = None,
        force_binary: bool = False,
    ) -> UploadResult:
        """Upload raw bytes.

        ``force_binary`` stores the object as ``application/octet-stream`` so the
        S3 console offers a download instead of previewing it inline.
        """
        settings = get_settings().s3
        target_bucket = bucket or settings.bucket
        if not target_bucket:
            raise UpstreamError("No S3 bucket configured (set AWS_S3_BUCKET).")

        extra: dict[str, str] = {}
        if force_binary:
            extra["ContentType"] = "application/octet-stream"
        elif content_type:
            extra["ContentType"] = content_type

        client = self._get_client()
        try:
            response = client.put_object(
                Bucket=target_bucket, Key=key, Body=data, **extra
            )
        except Exception as exc:
            log.error("S3 upload failed", extra={"key": key, "error": str(exc)[:300]})
            raise UpstreamError(f"Could not upload to S3: {exc}") from exc

        log.info("Uploaded to S3", extra={"bucket": target_bucket, "key": key, "bytes": len(data)})
        return UploadResult(
            bucket=target_bucket,
            key=key,
            url=f"https://{target_bucket}.s3.{settings.region}.amazonaws.com/{key}",
            size=len(data),
            etag=(response.get("ETag") or "").strip('"') or None,
        )

    def presigned_url(self, key: str, *, bucket: str | None = None, expires_in: int = 900) -> str:
        """Time-limited download URL — preferable to making objects public."""
        settings = get_settings().s3
        target_bucket = bucket or settings.bucket
        try:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": target_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            raise UpstreamError(f"Could not sign the S3 URL: {exc}") from exc


#: Shared instance. Constructing it does no I/O.
s3_service = S3Service()
