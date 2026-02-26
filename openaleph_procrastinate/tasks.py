import functools
import random
from typing import Any, Callable, cast

from anystore.logging import get_logger
from anystore.types import Uri
from procrastinate.app import App

from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Job, Status
from openaleph_procrastinate.tracer import get_tracer

log = get_logger(__name__)


def unpack_job(data: dict[str, Any]) -> AnyJob:
    """Unpack a payload to a job"""
    with ErrorHandler(log):
        if "dataset" in data:
            return DatasetJob(**data)
        return Job(**data)


def handle_trace(job: AnyJob, status: Status, tracer_uri: Uri | None) -> None:
    if tracer_uri is not None and isinstance(job, DatasetJob):
        tracer = get_tracer(job.queue, job.task, tracer_uri)
        for entity in job.get_entities():
            tracer.mark(cast(str, entity.id), status)


def task(app: App, **kwargs):
    # https://procrastinate.readthedocs.io/en/stable/howto/advanced/middleware.html
    tracer_uri = kwargs.pop("tracer_uri", None)

    def wrap(func: Callable[..., None]):
        def _inner(*job_args, **job_kwargs):
            # turn the json data into the job model instance
            job = unpack_job(job_kwargs)
            handle_trace(job, "doing", tracer_uri)
            try:
                func(*job_args, job)
                handle_trace(job, "succeeded", tracer_uri)
            except Exception as e:
                handle_trace(job, "failed", tracer_uri)
                raise e

        # need to call to not register tasks twice (procrastinate complains)
        wrapped_func = functools.update_wrapper(_inner, func, updated=())
        # call the original procrastinate task decorator with additional
        # configuration passed through
        return app.task(**kwargs)(wrapped_func)

    return wrap


class _Priorities:
    """
    Use different priority buckets in tasks:

    Example:
        ```python
        from openaleph_procrastinate.tasks import Priorities

        defer_task(payload, priority=Priorities.MEDIUM)
        ```
    """

    MAX = 100

    @property
    def ANY(self) -> int:
        return random.randint(1, 100)

    @property
    def LOW(self) -> int:
        return random.randint(1, 50)

    @property
    def MEDIUM(self) -> int:
        return random.randint(50, 70)

    @property
    def HIGH(self) -> int:
        return random.randint(70, 90)

    @property
    def USER(self) -> int:
        return random.randint(90, 99)


Priorities = _Priorities()
