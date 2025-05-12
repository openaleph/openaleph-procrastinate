"""
Access legacy Aleph servicelayer archive read-only without `servicelayer`
dendency
"""

from enum import StrEnum
from functools import cache

from anystore.store import BaseStore, get_store
from pydantic_settings import BaseSettings, SettingsConfigDict

from openaleph_procrastinate.exceptions import ArchiveFileNotFound


class ArchiveType(StrEnum):
    file = "file"
    s3 = "s3"
    gcs = "gcs"


class ArchiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="archive_")

    type: ArchiveType = ArchiveType.file
    bucket: str | None = None
    path: str | None = None
    endpoint_url: str | None = None


@cache
def get_archive() -> BaseStore:
    settings = ArchiveSettings()
    if settings.type == ArchiveType.s3:
        return get_store(f"s3://{settings.bucket}")
    if settings.type == ArchiveType.gcs:
        return get_store(f"gcs://{settings.bucket}")
    return get_store(uri=settings.path)


def lookup_key(content_hash: str) -> str:
    archive = get_archive()
    for key in archive.iterate_keys(prefix=content_hash):
        return key
    raise ArchiveFileNotFound(f"Key does not exist: `{content_hash}`")
