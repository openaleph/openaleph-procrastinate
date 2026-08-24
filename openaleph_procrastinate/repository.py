"""
Storage backends for the files and FollowTheMoney entities of a dataset.

During the transition to
[ftm-lakehouse](https://openaleph.org/docs/lib/ftm-lakehouse/usage/) both the
legacy stores (the Aleph *servicelayer* archive and the *followthemoney*
fragments store) and the lakehouse are available behind the same protocols.
Which one is used is decided by the
[`lakehouse`][openaleph_procrastinate.settings.OpenAlephSettings.lakehouse]
setting (`OPENALEPH_LAKEHOUSE=1`).
"""

from contextlib import ExitStack, contextmanager
from functools import cache
from pathlib import Path
from typing import Any, ContextManager, Generator, Iterable, Protocol, TypeAlias

from anystore.io.read import open_virtual
from anystore.logging import get_logger
from anystore.logic.io import stream
from anystore.logic.virtual import VirtualIO
from anystore.store import get_store
from anystore.util import uri_to_path
from followthemoney import EntityProxy
from ftm_lakehouse import get_archive as get_lakehouse_archive
from ftm_lakehouse import get_entities
from ftm_lakehouse.core.settings import CHECKSUM_ALGORITHM as LAKEHOUSE_CHECKSUM
from ftmq.query import M, Query
from ftmq.store.fragments import get_fragments
from ftmq.types import EntityProxies
from normality import safe_filename
from servicelayer import settings as sls
from servicelayer.archive import init_archive

from openaleph_procrastinate.exceptions import ArchiveFileNotFound
from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)

SERVICELAYER_CHECKSUM = "sha1"
"""Content hash algorithm of the legacy archive (the lakehouse uses sha256)"""

EntityIds: TypeAlias = str | Iterable[str] | None
"""An id filter: `None` means "everything", anything else "exactly these"."""


def get_sqlalchemy_pool() -> dict[str, int]:
    """Connection pool config for the (legacy) fragments store. It is part of
    the `ftmq` store cache key, so all call sites need to share it to not end
    up with a separate engine each."""
    settings = OpenAlephSettings()
    return {"pool_size": settings.db_pool_size, "max_overflow": settings.db_pool_size}


def ensure_ids(entity_ids: EntityIds) -> list[str] | None:
    """Normalize an id filter. An empty collection stays empty – it must never
    widen into "the whole dataset"."""
    if entity_ids is None:
        return None
    if isinstance(entity_ids, str):
        return [entity_ids]
    return list(entity_ids)


class Archive(Protocol):
    """Blob storage for the files being ingested."""

    def archive_file(
        self, file_path: Path, mime_type: str | None = None, origin: str | None = None
    ) -> str: ...

    def load_file(
        self, content_hash: str, temp_path: Path, file_name: str | None = None
    ) -> Path | None: ...

    def local_path(self, content_hash: str) -> ContextManager[Path]: ...

    def open(self, content_hash: str) -> ContextManager[VirtualIO]: ...


class EntityStore(Protocol):
    """Read and write access to the entities of one dataset."""

    def put(
        self,
        entity: EntityProxy,
        fragment: str | None = None,
        origin: str | None = None,
    ) -> None: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...

    def iterate(self, entity_ids: EntityIds = None) -> EntityProxies: ...

    def get(self, entity_id: str) -> EntityProxy | None: ...

    def delete(self) -> None: ...


class ServicelayerArchive:
    """The legacy Aleph servicelayer archive. It is global, it has no notion of
    a dataset, and it is configured via the `ARCHIVE_*` environment."""

    def __init__(self) -> None:
        self._archive = init_archive(
            archive_type=sls.ARCHIVE_TYPE,
            path=sls.ARCHIVE_PATH,
            bucket=sls.ARCHIVE_BUCKET,
            publication_bucket=sls.PUBLICATION_BUCKET,
            uri=sls.ARCHIVE_URI,
        )

    def archive_file(
        self, file_path: Path, mime_type: str | None = None, origin: str | None = None
    ) -> str:
        checksum: str = self._archive.archive_file(file_path, mime_type=mime_type)
        return checksum

    def load_file(
        self, content_hash: str, temp_path: Path, file_name: str | None = None
    ) -> Path | None:
        path: Path | None = self._archive.load_file(
            content_hash, file_name, str(temp_path)
        )
        return path

    @contextmanager
    def local_path(self, content_hash: str) -> Generator[Path, None, None]:
        """For a local archive this yields the archived file itself and leaves
        it alone; any other backend fetches it into a temporary directory that
        is cleaned up on exit."""
        path: Path | None = self._archive.load_file(content_hash)
        if path is None:
            raise ArchiveFileNotFound(f"File does not exist: `{content_hash}`")
        try:
            yield path
        finally:
            self._archive.cleanup_file(content_hash)

    @contextmanager
    def open(self, content_hash: str) -> Generator[VirtualIO, None, None]:
        with self.local_path(content_hash) as path:
            with open_virtual(path, algorithm=SERVICELAYER_CHECKSUM) as handler:
                yield handler


class LakehouseArchive:
    def __init__(self, dataset: str) -> None:
        self._archive = get_lakehouse_archive(dataset)
        self._is_local = self._archive._store.is_local

    def archive_file(
        self, file_path: Path, mime_type: str | None = None, origin: str | None = None
    ) -> str:
        file = self._archive.store(file_path, mimeType=mime_type, origin=origin)
        checksum: str = file.checksum
        return checksum

    def load_file(
        self, content_hash: str, temp_path: Path, file_name: str | None = None
    ) -> Path | None:
        if self._is_local:
            if self._archive.exists(content_hash):
                return uri_to_path(self._archive.to_uri(content_hash))
            return None
        try:
            with self._archive.open(content_hash) as handler:
                # mirror the layout servicelayer uses, so callers managing
                # their own temporary directory keep working
                key = f"{content_hash}.sl/{safe_filename(file_name, default='data')}"
                tmp = get_store(temp_path)
                with tmp.open(key, "wb") as out:
                    stream(handler, out)
                return uri_to_path(tmp.to_uri(key))
        except FileNotFoundError:
            # fsspec raises this instead of `anystore.exceptions.DoesNotExist`
            return None

    def _ensure_exists(self, content_hash: str) -> None:
        """`anystore` hands out a local path without looking, but a missing
        blob has to surface the same way it does for the legacy archive."""
        if not self._archive.exists(content_hash):
            raise ArchiveFileNotFound(f"Blob does not exist: `{content_hash}`")

    def local_path(self, content_hash: str) -> ContextManager[Path]:
        self._ensure_exists(content_hash)
        path: ContextManager[Path] = self._archive.local_path(content_hash)
        return path

    def open(self, content_hash: str) -> ContextManager[VirtualIO]:
        self._ensure_exists(content_hash)
        uri = self._archive.to_uri(content_hash)
        return open_virtual(uri, algorithm=LAKEHOUSE_CHECKSUM)


class FragmentStore:
    def __init__(self, dataset: str, origin: str | None = None) -> None:
        settings = OpenAlephSettings()
        self._db = get_fragments(
            dataset,
            origin,
            database_uri=settings.fragments_uri,
            **get_sqlalchemy_pool(),
        )
        self._writer = self._db.bulk()  # type: ignore[no-untyped-call]

    def put(
        self,
        entity: EntityProxy,
        fragment: str | None = None,
        origin: str | None = None,
    ) -> None:
        self._writer.put(entity, fragment=fragment, origin=origin)

    def flush(self) -> None:
        self._writer.flush()

    def close(self) -> None:
        """Flush. There is nothing else to release – the engine underneath
        belongs to the (cached) `ftmq` store and is shared with every other
        user of this dataset."""
        self.flush()

    def iterate(self, entity_ids: EntityIds = None) -> EntityProxies:
        ids = ensure_ids(entity_ids)
        if ids is not None and not ids:
            return
        self.flush()  # read back what this store just wrote
        yield from self._db.iterate(ids)

    def get(self, entity_id: str) -> EntityProxy | None:
        self.flush()
        return self._db.get(entity_id)

    def delete(self) -> None:
        self._db.delete()  # type: ignore[no-untyped-call]


class LakehouseStore:
    def __init__(self, dataset: str, origin: str | None = None) -> None:
        self._entities = get_entities(dataset)
        self._origin = origin
        self._stack: ExitStack | None = None
        self._writer: Any = None

    def _get_writer(self) -> Any:
        """Open the journal writer on first use and keep it open across puts
        and flushes – it buffers and upserts in batches itself, so staging
        entities in front of it would only duplicate that buffer, and every
        drop costs the writer context: a journal checkout and, on the way
        out, the `journal/last_updated` tag."""
        if self._writer is None:
            self._stack = ExitStack()
            self._writer = self._stack.enter_context(
                self._entities.writer(self._origin)
            )
        return self._writer

    def put(
        self,
        entity: EntityProxy,
        fragment: str | None = None,
        origin: str | None = None,
    ) -> None:
        self._get_writer().add_entity(entity, origin=origin, fragment=fragment)

    def flush(self) -> None:
        """Insert the buffered statements into the journal, keeping the writer
        open. Flushes the journal to parquet if it's full, but the final flush
        to parquet needs to be invoked manually by callers."""
        if self._writer is not None:
            self._writer.flush()

    def close(self) -> None:
        """Flush and hand the writer's connection back to the journal. Only
        here, not on every `flush`, for better performance."""
        if self._stack is not None:
            self._stack.close()  # flushes and closes the writer
            self._stack = None
            self._writer = None

    def iterate(self, entity_ids: EntityIds = None) -> EntityProxies:
        ids = ensure_ids(entity_ids)
        if ids is not None and not ids:
            return
        self.flush()
        q = Query()
        if ids:
            q = q.where(M(entity_id__in=ids))
        yield from self._entities.query(q, flush_first=True)

    def get(self, entity_id: str) -> EntityProxy | None:
        self.flush()
        entity: EntityProxy | None = self._entities.get(entity_id, flush_first=True)
        return entity

    def delete(self) -> None:
        self.close()
        self._entities.flush()
        self._entities._statements.destroy()


@cache
def get_archive(dataset: str) -> Archive:
    """Get the archive for a dataset. Archives are stateless, so this is
    cached – clear the cache to pick up changed `ARCHIVE_*` settings."""
    settings = OpenAlephSettings()
    if settings.lakehouse:
        return LakehouseArchive(dataset)
    return ServicelayerArchive()


def get_entity_store(dataset: str, origin: str | None = None) -> EntityStore:
    """Get the entity store for a dataset.

    Deliberately *not* cached: the stores buffer writes, and procrastinate runs
    sync tasks in a thread pool, so a shared instance would race on its buffer.
    The expensive handles underneath are cached by `ftmq` and `ftm_lakehouse`
    themselves, which makes building this wrapper cheap.
    """
    settings = OpenAlephSettings()
    if settings.lakehouse:
        return LakehouseStore(dataset, origin)
    return FragmentStore(dataset, origin)
