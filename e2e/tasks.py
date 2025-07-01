from anystore.logging import get_logger
from anystore.store import get_store

from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import AnyJob
from openaleph_procrastinate.tasks import task

log = get_logger(__name__)
app = make_app("e2e.tasks")


@task(app=app)
def dummy_task(job: AnyJob) -> None:
    job.log.info("👋", job=job)
    store = get_store(job.payload["path"])
    store.put("dummy_task", job.payload)
    job.task = "e2e.tasks.next_task"
    job.payload = {"path": store.uri}
    job.defer(app=app)


@task(app=app)
def next_task(job: AnyJob) -> None:
    log.info("I am the next job! 👋", job=job)
    store = get_store(job.payload["path"])
    store.touch("next_task")
