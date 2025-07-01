from anystore.logging import get_logger
from anystore.store import get_store
from procrastinate.job_context import JobContext

from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import AnyJob
from openaleph_procrastinate.tasks import task

log = get_logger(__name__)
app = make_app("tests.tasks")


@task(app=app, pass_context=True)
def dummy_task(context: JobContext, job: AnyJob) -> None:
    log.info("👋", job=job, context=context)
    store = get_store(job.payload["tmp_path"])
    store.put("dummy_task", job.payload)
    job.task = "tests.tasks.next_task"
    job.defer(app=app)


@task(app=app)
def next_task(job: AnyJob) -> None:
    log.info("I am the next job! 👋", job=job)
    store = get_store(job.payload["tmp_path"])
    store.touch("next_task")
