"""
The `Archive` and `EntityStore` protocols have to behave the same for the
legacy backends and for the lakehouse, so both are driven through the same
assertions here.
"""

from pathlib import Path

import pytest
from followthemoney import model
from ftm_lakehouse.repository.factories import clear_caches as lakehouse_clear_caches
from moto import mock_aws

from openaleph_procrastinate import repository
from openaleph_procrastinate.exceptions import ArchiveFileNotFound

DATASET = "test_dataset"
MISSING = "0" * 64  # a valid sha256 shape, so the lakehouse accepts it too


def clear_caches() -> None:
    repository.get_archive.cache_clear()
    lakehouse_clear_caches()


@pytest.fixture
def legacy(monkeypatch, tmp_path):
    """The servicelayer archive plus the followthemoney fragments store"""
    monkeypatch.setenv("OPENALEPH_LAKEHOUSE", "0")
    monkeypatch.setenv("FTM_FRAGMENTS_URI", f"sqlite:///{tmp_path / 'fragments.db'}")
    # `servicelayer` reads its archive config into module constants at import
    # time, so setting the environment doesn't reach it
    monkeypatch.setattr("servicelayer.settings.ARCHIVE_TYPE", "file")
    monkeypatch.setattr("servicelayer.settings.ARCHIVE_PATH", str(tmp_path / "archive"))
    clear_caches()
    yield
    clear_caches()


@pytest.fixture
def lakehouse(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENALEPH_LAKEHOUSE", "1")
    monkeypatch.setenv("LAKEHOUSE_URI", str(tmp_path / "lakehouse"))
    # the journal defaults to an in-memory sqlite shared by the whole process
    monkeypatch.setenv("LAKEHOUSE_JOURNAL_URI", f"sqlite:///{tmp_path / 'journal.db'}")
    clear_caches()
    from ftm_lakehouse import ensure_dataset

    ensure_dataset(DATASET)
    yield
    clear_caches()


@pytest.fixture(params=["legacy", "lakehouse"])
def backend(request):
    """Both storage backends, so the protocols stay in sync"""
    request.getfixturevalue(request.param)
    return request.param


def make_entity(entity_id: str, name: str = "Jane"):
    entity = model.get_proxy({"id": entity_id, "schema": "Person"})
    entity.add("name", name)
    return entity


# --- Archive ---------------------------------------------------------------


# @mock_aws
def test_archive_roundtrip(backend, fixtures_path, tmp_path):
    store = repository.get_archive(DATASET)
    checksum = store.archive_file(fixtures_path / "hello.txt", mime_type="text/plain")
    assert checksum

    # a path for external tools
    with store.local_path(checksum) as path:
        assert isinstance(path, Path)
        assert path.exists()
        assert path.read_bytes().decode().strip() == "world"

    # an open handler carrying the content hash
    with store.open(checksum) as handler:
        assert handler.checksum == checksum
        assert handler.read().decode().strip() == "world"
        assert handler.path.exists()

    # a copy the caller owns and cleans up itself
    temp_path = tmp_path / "workdir"
    local = store.load_file(checksum, temp_path, "hello.txt")
    assert local is not None
    assert local.exists()
    assert local.read_bytes().decode().strip() == "world"


# @mock_aws
def test_archive_miss(backend, tmp_path):
    """A blob that isn't there is a miss for `load_file`, an error otherwise"""
    store = repository.get_archive(DATASET)
    assert store.load_file(MISSING, tmp_path) is None
    with pytest.raises(ArchiveFileNotFound):
        with store.local_path(MISSING):
            pass
    with pytest.raises(ArchiveFileNotFound):
        with store.open(MISSING):
            pass


# --- EntityStore -----------------------------------------------------------


def test_entities_roundtrip(backend):
    store = repository.get_entity_store(DATASET)
    store.put(make_entity("jane"))
    store.put(make_entity("john", "John"))
    store.flush()

    jane = store.get("jane")
    assert jane is not None
    assert jane.id == "jane"
    assert "Jane" in jane.get("name")

    assert store.get("nobody") is None


def test_entities_iterate_by_ids(backend):
    store = repository.get_entity_store(DATASET)
    for ix in range(5):
        store.put(make_entity(f"e-{ix}"))
    store.flush()

    assert {e.id for e in store.iterate(["e-1", "e-3"])} == {"e-1", "e-3"}
    assert {e.id for e in store.iterate("e-2")} == {"e-2"}
    # `None` means everything ...
    assert len({e.id for e in store.iterate()}) == 5
    # ... but an empty selection must never widen into the whole dataset
    assert list(store.iterate([])) == []


def test_entities_writer_flushes_on_exit(backend):
    from openaleph_procrastinate import helpers

    with helpers.entity_writer(DATASET) as writer:
        writer.put(make_entity("buffered"))

    # a *different* store instance sees it, so it really was written
    assert repository.get_entity_store(DATASET).get("buffered") is not None


def test_entities_read_back_own_writes(backend):
    """Reads flush the store's own pending writes first"""
    store = repository.get_entity_store(DATASET)
    store.put(make_entity("unflushed"))
    assert store.get("unflushed") is not None


def test_entity_store_is_not_shared(backend):
    """Stores buffer writes and tasks run in threads, so they must not be
    handed out from a cache"""
    assert repository.get_entity_store(DATASET) is not repository.get_entity_store(
        DATASET
    )


# --- job payloads ----------------------------------------------------------


def test_lakehouse_payload_keeps_full_entity(lakehouse, monkeypatch):
    """Under the lakehouse `load_entities` reads straight from the payload, so
    `from_entities` must not reduce entities to stubs - not even when a caller
    explicitly asks for it."""
    from openaleph_procrastinate import model as model_module
    from openaleph_procrastinate.model import DatasetJob
    from openaleph_procrastinate.settings import OpenAlephSettings

    settings = OpenAlephSettings()
    assert not settings.procrastinate_dehydrate_entities
    # `model` builds its settings singleton at import time
    monkeypatch.setattr(model_module, "settings", settings)

    entity = make_entity("full", "Jane Doe")
    job = DatasetJob.from_entities(
        DATASET, "q", "t", [entity], dehydrate=True  # explicitly asked for
    )
    loaded = list(job.load_entities())
    assert len(loaded) == 1
    assert loaded[0].get("name") == ["Jane Doe"]


# --- servicelayer archive backends -----------------------------------------


@mock_aws
@pytest.mark.parametrize("archive_type", ["file", "s3"])
def test_servicelayer_local_path_lifetime(
    legacy, monkeypatch, tmp_path, fixtures_path, archive_type
):
    """A local archive hands out the archived file itself and keeps it; any
    other backend hands out a temporary copy and cleans it up on exit."""
    monkeypatch.setattr("servicelayer.settings.ARCHIVE_TYPE", archive_type)
    monkeypatch.setattr("servicelayer.settings.ARCHIVE_BUCKET", "openaleph")
    repository.get_archive.cache_clear()

    store = repository.get_archive(DATASET)
    checksum = store.archive_file(fixtures_path / "hello.txt")

    with store.local_path(checksum) as path:
        assert path.exists()
    assert path.exists() is (archive_type == "file")

    with store.open(checksum) as handler:
        assert handler.checksum == checksum
        assert handler.read().decode().strip() == "world"
    assert handler.path.exists() is (archive_type == "file")
