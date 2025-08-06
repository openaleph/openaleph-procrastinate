import functools
import random
from typing import Any, Callable

from anystore.logging import get_logger
from procrastinate.app import App

from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Job

log = get_logger(__name__)


def unpack_job(data: dict[str, Any]) -> AnyJob:
    """Unpack a payload to a job"""
    with ErrorHandler(log):
        if "dataset" in data:
            return DatasetJob(**data)
        return Job(**data)


def task(app: App, **kwargs):
    # https://procrastinate.readthedocs.io/en/stable/howto/advanced/middleware.html
    def wrap(func: Callable[..., None]):
        def _inner(*job_args, **job_kwargs):
            # turn the json data into the job model instance
            job = unpack_job(job_kwargs)
            func(*job_args, job)

        # need to call to not register tasks twice (procrastinate complains)
        wrapped_func = functools.update_wrapper(_inner, func, updated=())
        # call the original procrastinate task decorator with additional
        # configuration passed through
        return app.task(**kwargs)(wrapped_func)

    return wrap


class Priorities:
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
