"""
Helper functions to access the archive and FollowTheMoney entities of a dataset
within Jobs.

Everything here goes through
[the repository][openaleph_procrastinate.repository], which speaks to either
the legacy stores or the lakehouse depending on the
[`lakehouse`][openaleph_procrastinate.settings.OpenAlephSettings.lakehouse]
setting.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager, Generator, Iterable

from anystore.logic.virtual import VirtualIO
from ftmq.types import EntityProxies

from openaleph_procrastinate.repository import (
    EntityStore,
    get_archive,
    get_entity_store,
)

OPAL_ORIGIN = "openaleph_procrastinate"


def get_localpath(dataset: str, content_hash: str) -> ContextManager[Path]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. The file is cleaned up after leaving the context.
    [Reference][openaleph_procrastinate.model.DatasetJob.get_file_references]
    """
    return get_archive(dataset).local_path(content_hash)


def open_file(dataset: str, content_hash: str) -> ContextManager[VirtualIO]:
    """
    Load a file from the archive and store it in a local temporary path for
    further processing. Returns an open file handler. The file is closed and
    cleaned up after leaving the context.
    [Reference][openaleph_procrastinate.model.DatasetJob.get_file_references]
    """
    return get_archive(dataset).open(content_hash)


def load_entities(dataset: str, entity_ids: Iterable[str]) -> EntityProxies:
    """
    Batch retrieve entities from the entity store.
    """
    yield from get_entity_store(dataset).iterate(entity_ids)


@contextmanager
def entity_writer(
    dataset: str, origin: str = OPAL_ORIGIN
) -> Generator[EntityStore, None, None]:
    """
    Get the [`EntityStore`][openaleph_procrastinate.repository.EntityStore] for
    the given `dataset` to write to. It is flushed and closed when leaving the
    context – a store that buffers writes holds a database connection until
    then, so callers that build one themselves have to close it.
    """
    store = get_entity_store(dataset, origin)
    try:
        yield store
    finally:
        store.close()
