"""
Access legacy Aleph servicelayer archive read-only without `servicelayer`
dendency
"""

from enum import StrEnum
from functools import cache

from anystore.store import BaseStore, get_store
from anystore.types import Uri
from pydantic_settings import BaseSettings, SettingsConfigDict

from openaleph_procrastinate.exceptions import ArchiveFileNotFound


def make_checksum_key(ch: str) -> str:
    if len(ch) < 6:
        raise ValueError(f"Invalid checksum: `{ch}`")
    return "/".join((ch[:2], ch[2:4], ch[4:6], ch))


class ArchiveType(StrEnum):
    file = "file"
    s3 = "s3"
    gcs = "gcs"


class ArchiveSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="archive_", env_file=".env", extra="ignore"
    )

    type: ArchiveType = ArchiveType.file
    bucket: str | None = None
    path: str | None = None
    endpoint_url: str | None = None


@cache
def get_archive(uri: Uri | None = None) -> BaseStore:
    if uri is not None:
        return get_store(uri=uri)
    settings = ArchiveSettings()
    if settings.type == ArchiveType.s3:
        return get_store(f"s3://{settings.bucket}")
    if settings.type == ArchiveType.gcs:
        return get_store(f"gcs://{settings.bucket}")
    return get_store(uri=settings.path)


def lookup_key(checksum: str, archive: BaseStore | None = None) -> str:
    archive = archive or get_archive()
    prefix = make_checksum_key(checksum)
    for key in archive.iterate_keys(prefix=prefix):
        return key
    raise ArchiveFileNotFound(f"Key does not exist: `{prefix}`")
