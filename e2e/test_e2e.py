import random

from anystore.io import smart_stream_json

from e2e.tasks import app
from openaleph_procrastinate.app import run_sync_worker
from openaleph_procrastinate.manage.db import Db, get_db
from openaleph_procrastinate.manage.status import get_dataset_status, get_status
from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.tasks import unpack_job


def _setup_db() -> Db:
    settings = OpenAlephSettings()
    assert not settings.in_memory_db
    assert not settings.procrastinate_sync

    db = get_db()
    db._destroy()
    db.configure()
    return db


def test_e2e_psql_cancel():
    db = _setup_db()

    payloads = list(smart_stream_json("./jobs.json"))
    with app.open():
        for job in map(unpack_job, payloads):
            job.defer(app)

    todo = [job for job in app.job_manager.list_jobs() if job.status == "todo"]
    assert len(todo) == 2

    db.cancel_jobs(task="e2e.tasks.dummy_task")
    todo = [job for job in app.job_manager.list_jobs() if job.status == "todo"]
    assert len(todo) == 0


def test_e2e_psql_status():
    db = _setup_db()

    queues = ["q", "b"]
    batches = ["1", "2"]
    datasets = ["d1", "d2"]
    some_jobs_will_fail = [
        DatasetJob(
            queue=random.choice(queues),
            batch=random.choice(batches),
            dataset=random.choice(datasets),
            task="e2e.tasks.task_with_errors",
        )
        for _ in range(10)
    ]
    with app.open():
        for job in some_jobs_will_fail:
            job.defer(app)

    datasets = {d.name: d for d in get_status(active_only=False)}
    assert set(datasets.keys()) == {"d1", "d2"}

    for dataset in datasets.values():
        assert len(dataset.batches)
        for batch in dataset.batches:
            assert len(batch.queues)
            for queue in batch.queues:
                assert len(queue.tasks)
    assert datasets["d1"].total + datasets["d2"].total == 10
    assert datasets["d1"].todo + datasets["d2"].todo == 10
    assert datasets["d1"].doing + datasets["d2"].doing == 0
    assert all(d.is_active() for d in datasets.values())
    assert not any(d.is_running() for d in datasets.values())

    run_sync_worker(app)

    datasets = {d.name: d for d in get_status(active_only=False)}
    assert datasets["d1"].total + datasets["d2"].total == 10
    assert datasets["d1"].doing + datasets["d2"].doing == 0
    assert datasets["d1"].failed + datasets["d2"].failed > 0
    assert not any(d.is_running() for d in datasets.values())
    assert not any(d.is_active() for d in datasets.values())

    d1 = get_dataset_status("d1", active_only=False)
    assert d1 is not None

    assert len(list(db.iterate_jobs())) == 10
    d1_jobs = list(db.iterate_jobs(dataset="d1"))
    assert len(d1_jobs) == d1.total
    failed = list(db.iterate_jobs(status="failed"))
    assert len(failed) < 10
    failed = list(db.iterate_jobs(dataset="d1", status="failed"))
    assert len(failed) == d1.failed
    assert len(failed) <= d1.total

    assert d1.took is not None
    assert d1.took.total_seconds() > 0
