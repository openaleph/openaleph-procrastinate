from anystore.store import get_store

from openaleph_procrastinate.model import Job


def test_defer(app, tmp_path):
    job = Job(
        queue="test", task="tests.tasks.dummy_task", payload={"tmp_path": str(tmp_path)}
    )
    job.defer(app=app)

    # Access all the existing jobs
    jobs = app.connector.jobs
    assert len(jobs) == 1

    # Run the jobs
    app.run_worker(wait=False)

    store = get_store(tmp_path)
    assert store.get("dummy_task") == {"tmp_path": str(tmp_path)}
    assert store.exists("next_task")
