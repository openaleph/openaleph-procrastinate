from anystore.store import get_store
from followthemoney import model as ftm_model
from procrastinate.testing import InMemoryConnector

from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import DatasetJob


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

    store = get_store(tmp_path)
    assert store.get("traced_test-entity-123") is True
