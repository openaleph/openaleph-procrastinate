import functools
from typing import Any

from anystore.logging import get_logger
from procrastinate.app import App

from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Defers, Job

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
            defer: Defers = func(*job_args, job)
            # defer next jobs
            if defer is not None:
                for job in defer:
                    job.defer(app)

        wrapped_func = functools.update_wrapper(new_func, func, updated=())
        return app.task(**kwargs)(wrapped_func)

    if not original_func:
        return wrap

    return wrap(original_func)
