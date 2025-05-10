"""
Helper functions to access Archive and FollowTheMoney data within Jobs
"""

from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import BinaryIO, Generator

from followthemoney.proxy import EntityProxy
from ftmstore import get_dataset
from ftmstore.loader import BulkLoader
from servicelayer.archive import init_archive
from servicelayer.archive.archive import Archive

from openaleph_procrastinate.exceptions import ArchiveFileNotFound, EntityNotFound
from openaleph_procrastinate.settings import settings

OPAL_ORIGIN = "openaleph_procrastinate"


@cache
def get_archive() -> Archive:
    return init_archive()


@contextmanager
def get_localpath(content_hash: str) -> Generator[Path, None, None]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. The file is cleaned up after leaving the context.
    """
    archive = get_archive()
    path = archive.load_file(content_hash)
    if path is None:
        raise ArchiveFileNotFound(f"Key does not exist: `{content_hash}`")
    try:
        yield Path(path)
    finally:
        archive.cleanup_file(content_hash)


@contextmanager
def open_file(content_hash: str) -> Generator[BinaryIO, None, None]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. Returns an open file handler. The file is closed and
    cleaned up after leaving the context.
    """
    with get_localpath(content_hash) as path:
        handler = path.open("rb")
        try:
            yield handler
        finally:
            handler.close()


def load_entity(dataset: str, entity_id: str) -> EntityProxy:
    """
    Retrieve a single entity from the store.
    """
    store = get_dataset(dataset, database_uri=settings.ftm_store_uri)
    entity = store.get(entity_id)
    if entity is None:
        raise EntityNotFound(f"Entity `{entity_id}` not found in dataset `{dataset}`")
    return entity


@contextmanager
def entity_writer(dataset: str) -> Generator[BulkLoader, None, None]:
    """
    Get the `ftmstore.dataset.BulkLoader` for the given `dataset`. The entities
    are flushed when leaving the context.
    """
    store = get_dataset(
        dataset, origin=OPAL_ORIGIN, database_uri=settings.ftm_store_uri
    )
    loader = store.bulk()
    try:
        yield loader
    finally:
        loader.flush()
