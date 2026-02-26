from anystore.logging import get_logger
from anystore.store import get_store
from procrastinate.job_context import JobContext

from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import AnyJob, DatasetJob
from openaleph_procrastinate.tasks import task
from openaleph_procrastinate.tracer import Tracer

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


@task(app=app, tracer_uri="memory://")
def traced_task(job: AnyJob) -> None:
    assert isinstance(job, DatasetJob)
    tracer = Tracer(job.queue, job.task, "memory://")
    store = get_store(job.payload["tmp_path"])
    for entity in job.get_entities():
        store.put(f"traced_{entity.id}", tracer.is_processing(str(entity.id)))
