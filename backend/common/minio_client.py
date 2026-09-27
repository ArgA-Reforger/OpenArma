"""MinIO client wrapper, providing file upload/download/delete operations."""

from io import BytesIO

from minio import Minio
from minio.error import S3Error

from backend.core.conf import settings


def _get_client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket() -> None:
    client = _get_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


def upload_file(object_name: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
    """
    Upload a file to MinIO.

    :param object_name: object path, e.g. knowledge/123/456/file.pdf
    :param data: file byte content
    :param content_type: MIME type
    :return: object path
    """
    client = _get_client()
    ensure_bucket()
    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_name


def download_file(object_name: str) -> bytes:
    client = _get_client()
    response = client.get_object(settings.MINIO_BUCKET, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(object_name: str) -> None:
    client = _get_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, object_name)
    except S3Error:
        pass


def get_presigned_url(object_name: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta

    client = _get_client()
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )
