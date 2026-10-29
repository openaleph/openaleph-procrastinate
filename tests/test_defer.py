from anystore.store import get_store
from followthemoney import model
from followthemoney.proxy import EntityProxy
from procrastinate.testing import InMemoryConnector

from openaleph_procrastinate import defer
from openaleph_procrastinate.app import App, make_app
from openaleph_procrastinate.model import DatasetJob, Job
from openaleph_procrastinate.tasks import unpack_job

INGEST_TASK = "ingestors.tasks.ingest"


def test_defer(tmp_path):
    app = make_app("tests.tasks")
    assert isinstance(app.connector, InMemoryConnector)

    job = Job(
        queue="test", task="tests.tasks.dummy_task", payload={"tmp_path": str(tmp_path)}
    )
    job.defer(app=app)  # this runs the worker already (testing)

    # Access all the existing jobs
    jobs = app.connector.jobs
    assert len(jobs) == 2

    store = get_store(tmp_path)
    assert store.get("dummy_task") == {"tmp_path": str(tmp_path)}
    assert store.exists("next_task")


def dedupe_app(monkeypatch) -> App:
    """An app whose deferred jobs stay in the queue. `DEBUG=1` and
    `PROCRASTINATE_SYNC=1` in the test env run them inline, and a job that
    leaves `todo` releases its queueing lock."""
    monkeypatch.setattr("openaleph_procrastinate.model.settings.debug", False)
    return App(connector=InMemoryConnector())


def make_entity(entity_id: str) -> EntityProxy:
    entity = model.get_proxy({"id": entity_id, "schema": "Document"})
    entity.add("contentHash", "deadbeef")
    return entity


def make_job(*entity_ids: str) -> DatasetJob:
    return DatasetJob.from_entities(
        dataset="test",
        queue="ingest",
        task=INGEST_TASK,
        entities=[make_entity(i) for i in entity_ids],
    )


def test_defer_packs_entities(monkeypatch):
    app = dedupe_app(monkeypatch)
    job = make_job("a", "b")
    job.defer(app)
    (row,) = app.connector.jobs.values()
    assert isinstance(row["args"]["payload"]["entities"], str)
    assert row["args"]["dataset"] == "test"
    assert unpack_job(row["args"]).payload["entities"] == job.payload["entities"]


def test_queueing_lock_keys_on_task_dataset_and_entities():
    assert make_job("a").get_queueing_lock() == f"{INGEST_TASK}:test:a"
    assert make_job("a").get_queueing_lock() != make_job("b").get_queueing_lock()
    # the entities are a set, their order in the payload is not part of the key
    assert (
        make_job("a", "b").get_queueing_lock() == make_job("b", "a").get_queueing_lock()
    )
    job = DatasetJob(dataset="test", queue="ingest", task=INGEST_TASK, payload={})
    assert job.get_queueing_lock() is None


def test_queueing_lock_is_hashed_when_it_grows():
    """The unique index on `queueing_lock` is a btree and rejects a long entry."""
    lock = make_job(*[f"entity-{i:04d}" for i in range(100)]).get_queueing_lock()
    assert lock.startswith(f"{INGEST_TASK}:test:")
    assert len(lock) < 128


def test_ingest_defers_once_while_the_job_waits(monkeypatch):
    app = dedupe_app(monkeypatch)
    entity = make_entity("a")
    assert defer.ingest(app, "test", [entity]) is True
    assert defer.ingest(app, "test", [entity]) is False
    assert len(app.connector.jobs) == 1
    assert defer.ingest(app, "test", [make_entity("b")]) is True
    assert len(app.connector.jobs) == 2


def test_ingest_dedupe_can_be_turned_off(monkeypatch):
    app = dedupe_app(monkeypatch)
    monkeypatch.setattr(defer.tasks.ingest, "dedupe", False)
    entity = make_entity("a")
    assert defer.ingest(app, "test", [entity]) is True
    assert defer.ingest(app, "test", [entity]) is True
    assert len(app.connector.jobs) == 2


def test_ingest_without_deferring(monkeypatch):
    app = dedupe_app(monkeypatch)
    monkeypatch.setattr(defer.tasks.ingest, "defer", False)
    assert defer.ingest(app, "test", [make_entity("a")]) is False
    assert not app.connector.jobs
