"""
Helper functions to access Archive and FollowTheMoney data within Jobs
"""

from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager, Generator

from anystore.store.virtual import VirtualIO, get_virtual_path, open_virtual
from followthemoney.proxy import EntityProxy
from ftmstore import get_dataset
from ftmstore.loader import BulkLoader

from openaleph_procrastinate.archive import get_archive, lookup_key
from openaleph_procrastinate.exceptions import EntityNotFound
from openaleph_procrastinate.settings import OpenAlephSettings

OPAL_ORIGIN = "openaleph_procrastinate"
settings = OpenAlephSettings()


def get_localpath(dataset: str, content_hash: str) -> ContextManager[Path]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. The file is cleaned up after leaving the context.
    [Reference][openaleph_procrastinate.model.DatasetJob.get_file_references]
    """
    archive = get_archive()
    key = lookup_key(content_hash)
    return get_virtual_path(key, archive)


def open_file(dataset: str, content_hash: str) -> ContextManager[VirtualIO]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. Returns an open file handler. The file is closed and
    cleaned up after leaving the context.
    [Reference][openaleph_procrastinate.model.DatasetJob.get_file_references]
    """
    archive = get_archive()
    key = lookup_key(content_hash)
    return open_virtual(key, archive)


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
    Get the `ftmstore.dataset.BulkLoader` for the given `dataset`. The writer is
    flushed when leaving the context.
    """
    store = get_dataset(
        dataset, origin=OPAL_ORIGIN, database_uri=settings.ftm_store_uri
    )
    loader = store.bulk()
    try:
        yield loader
    finally:
        loader.flush()
