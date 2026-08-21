from anystore.store import get_store
from followthemoney import model as ftm_model
from procrastinate.testing import InMemoryConnector

from openaleph_procrastinate import tasks
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.tracer import get_job_tracer


def test_traced_task(tmp_path):
    app = make_app("tests.tasks")
    assert isinstance(app.connector, InMemoryConnector)

    # Reset stale notification handler from previous tests — the cached
    # InMemoryConnector may still reference a closed event loop from an
    # earlier sync worker run, causing _notify to fail with
    # "Event loop is closed" when it tries cross-thread scheduling.
    app.connector.on_notification = None

    entity = ftm_model.make_entity("Person")
    entity.id = "test-entity-123"
    entity.add("name", "Test Person")

    job = DatasetJob(
        dataset="test-dataset",
        queue="test",
        task="tests.tasks.traced_task",
        payload={
            "entities": [entity.to_dict()],
            "tmp_path": str(tmp_path),
        },
    )
    job.defer(app=app)

    # check traced processing status written by the task
    store = get_store(tmp_path)
    assert store.get("traced_test-entity-123") is True
    # check succeeded
    tracer = get_job_tracer(job, "memory://")
    assert tracer.get("succeeded") == 1


def test_tracer_flush_threshold(tmp_path, monkeypatch):
    """Processed entities are counted per dataset and flush the lakehouse
    journal once they reach the threshold."""
    monkeypatch.setattr(tasks.settings, "lakehouse", True)
    monkeypatch.setattr(tasks.settings, "lakehouse_flush_threshold", 3)

    flushed: list[str] = []

    class FakeEntities:
        def __init__(self, dataset: str) -> None:
            self.dataset = dataset

        def flush(self) -> None:
            flushed.append(self.dataset)

    monkeypatch.setattr(tasks, "get_lakehouse_entities", FakeEntities)

    app = make_app("tests.tasks")

    def defer(*entity_ids: str) -> DatasetJob:
        # see `test_traced_task`: each sync worker run leaves a notification
        # handler behind that is bound to its now closed event loop
        app.connector.on_notification = None
        entities = []
        for entity_id in entity_ids:
            entity = ftm_model.make_entity("Person")
            entity.id = entity_id
            entity.add("name", entity_id)
            entities.append(entity.to_dict())
        # own queue: the tracer counters are keyed by queue and task
        job = DatasetJob(
            dataset="flush-dataset",
            queue="test-flush",
            task="tests.tasks.traced_task",
            payload={"entities": entities, "tmp_path": str(tmp_path)},
        )
        job.defer(app=app)
        return job

    job = defer("e-1", "e-2")
    tracer = get_job_tracer(job, "memory://")

    # processed 2 entities
    assert tracer.get(tasks.PENDING_FLUSH) == 2
    assert flushed == []

    defer("e-3", "e-4")

    # threshold reached: flushed once, the surplus carries over
    assert flushed == ["flush-dataset"]
    assert tracer.get(tasks.PENDING_FLUSH) == 1
