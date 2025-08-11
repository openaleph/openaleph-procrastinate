from anystore.io import smart_stream_json

from e2e.tasks import app
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.tasks import cancel_jobs_per_task, unpack_job


def test_e2e_cancel():
    """Tests for postgres"""

    settings = OpenAlephSettings()
    assert not settings.in_memory_db
    assert not settings.procrastinate_sync

    payloads = list(smart_stream_json("./jobs.json"))
    with app.open():
        for job in map(unpack_job, payloads):
            job.defer(app)

    todo = [job for job in app.job_manager.list_jobs() if job.status == "todo"]
    assert len(todo) == 2

    cancel_jobs_per_task("e2e.tasks.dummy_task")
    todo = [job for job in app.job_manager.list_jobs() if job.status == "todo"]
    assert len(todo) == 0
