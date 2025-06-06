import functools
from typing import Any

from anystore.logging import get_logger
from procrastinate.app import App
from procrastinate.job_context import JobContext

from openaleph_procrastinate.app import app
from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Job, Stage

log = get_logger(__name__)


def unpack_job(data: dict[str, Any]) -> AnyJob:
    """Unpack a payload to a job"""
    with ErrorHandler(log):
        if "dataset" in data:
            return DatasetJob(**data)
        return Job(**data)


def task(original_func=None, **kwargs):
    # https://procrastinate.readthedocs.io/en/stable/howto/advanced/middleware.html
    def wrap(func):
        app: App = kwargs.pop("app")

        def new_func(*job_args, **job_kwargs):
            # turn the json data into the job model instance
            job = unpack_job(job_kwargs)
            result: AnyJob | None = func(*job_args, job)
            # propagate to next stage if any:
            if result is not None and result.stages:
                next_stage = result.stages.pop()
                next_job = next_stage.make_job(result)
                next_job.defer(app)
            return result

        wrapped_func = functools.update_wrapper(new_func, func, updated=())
        return app.task(**kwargs)(wrapped_func)

    if not original_func:
        return wrap

    return wrap(original_func)


@task(app=app, pass_context=True)
def dummy_task(context: JobContext, job: AnyJob) -> AnyJob:
    """
    A dummy task for testing purposes
    """
    log.info("👋", job=job, context=context)
    job.stages = [
        Stage(queue=job.queue, task="openaleph_procrastinate.tasks.next_task")
    ]
    return job


@task(app=app)
def next_task(job: AnyJob):
    """
    A dummy task for testing purposes
    """
    log.info("I am the next job! 👋", job=job)
