"""
Helper functions to access Archive and FollowTheMoney data within Jobs
"""

from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Generator

from anystore.store.virtual import get_virtual
from followthemoney.proxy import EntityProxy
from ftmstore import get_dataset
from ftmstore.loader import BulkLoader

from openaleph_procrastinate.exceptions import EntityNotFound
from openaleph_procrastinate.legacy.archive import get_archive, lookup_key
from openaleph_procrastinate.settings import settings

OPAL_ORIGIN = "openaleph_procrastinate"


@contextmanager
def get_localpath(dataset: str, content_hash: str) -> Generator[Path, None, None]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. The file is cleaned up after leaving the context.

    !!! danger
        This is not tested.
    """
    archive = get_archive()
    key = lookup_key(content_hash)
    store = get_virtual()
    path = store.download(key, archive)
    try:
        yield Path(path)
    finally:
        store.cleanup(path)


@contextmanager
def open_file(dataset: str, content_hash: str) -> Generator[BinaryIO, None, None]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. Returns an open file handler. The file is closed and
    cleaned up after leaving the context.

    !!! danger
        This is not tested.
    """
    archive = get_archive()
    key = lookup_key(content_hash)
    with archive.open(key) as handler:
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
