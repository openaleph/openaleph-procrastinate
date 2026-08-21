import functools
import random
from typing import Any, Callable, cast

from anystore.logging import get_logger
from ftm_lakehouse import get_entities as get_lakehouse_entities
from procrastinate.app import App

from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Job, Status
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.tracer import Tracer, get_job_tracer

log = get_logger(__name__)
settings = OpenAlephSettings()

PENDING_FLUSH = "pending_flush"


def unpack_job(data: dict[str, Any]) -> AnyJob:
    """Unpack a payload to a job"""
    with ErrorHandler(log):
        if "dataset" in data:
            return DatasetJob(**data)
        return Job(**data)


def handle_trace(entity_ids: list[str], status: Status, tracer: Tracer) -> None:
    for entity_id in entity_ids:
        tracer.mark(entity_id, status)
    if status in ("succeeded", "failed"):
        tracer.incr(status, 1)
        tracer.incr(PENDING_FLUSH, len(entity_ids))


def handle_flush(dataset: str, tracer: Tracer) -> None:
    """Flush the lakehouse journal to parquet once enough entities have been
    processed."""
    if not settings.lakehouse or settings.lakehouse_flush_threshold < 1:
        return
    if (tracer.get(PENDING_FLUSH) or 0) >= settings.lakehouse_flush_threshold:
        # subtract before flushing: a concurrent worker shouldn't flush the
        # same batch again, and the overflow carries over to the next one
        tracer.incr(PENDING_FLUSH, -settings.lakehouse_flush_threshold)
        log.info("Flushing lakehouse journal ...", dataset=dataset)
        get_lakehouse_entities(dataset).flush()


def task(app: App, **kwargs):
    # https://procrastinate.readthedocs.io/en/stable/howto/advanced/middleware.html
    tracer_uri = kwargs.pop("tracer_uri", None)

    def wrap(func: Callable[..., None]):
        def _inner(*job_args, **job_kwargs):
            # turn the json data into the job model instance
            job = unpack_job(job_kwargs)
            tracer = None
            entity_ids = []
            if tracer_uri and isinstance(job, DatasetJob):
                tracer = get_job_tracer(job, tracer_uri)
                entity_ids = list([cast(str, e.id) for e in job.get_entities()])
                handle_trace(entity_ids, "doing", tracer)
            try:
                func(*job_args, job)
                if tracer:
                    handle_trace(entity_ids, "succeeded", tracer)
            except Exception as e:
                if tracer:
                    handle_trace(entity_ids, "failed", tracer)
                raise e
            if tracer:
                handle_flush(job.dataset, tracer)

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
