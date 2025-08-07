import psycopg
import functools
import random
from typing import Any, Callable

from anystore.logging import get_logger
from procrastinate.app import App

from openaleph_procrastinate.exceptions import ErrorHandler
from openaleph_procrastinate.model import AnyJob, DatasetJob, Job
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.app import make_app

log = get_logger(__name__)
app = make_app()


def unpack_job(data: dict[str, Any]) -> AnyJob:
    """Unpack a payload to a job"""
    with ErrorHandler(log):
        if "dataset" in data:
            return DatasetJob(**data)
        return Job(**data)


def get_job_ids_by_criteria(query: str, job_filter: str) -> list[int] | list:
    settings = OpenAlephSettings()
    db_uri = settings.procrastinate_db_uri

    job_ids = []
    with psycopg.connect(db_uri) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (job_filter,))
            job_ids = cursor.fetchall()

    if job_ids:
        job_ids = [data[0] for data in job_ids]

    return job_ids


def cancel_jobs(job_ids: list[int]) -> None:
    with app.open():
        for job_id in job_ids:
            app.job_manager.cancel_job_by_id(job_id)


def cancel_jobs_per_dataset(dataset: str) -> None:
    query = """SELECT id FROM procrastinate_jobs WHERE (args->>'dataset') = (%s)"""
    job_ids = get_job_ids_by_criteria(query, dataset)
    if job_ids:
        cancel_jobs(job_ids)


def cancel_jobs_per_queue(queue_name: str) -> None:
    query = """SELECT id FROM procrastinate_jobs WHERE queue_name = (%s)"""
    job_ids = get_job_ids_by_criteria(query, queue_name)
    if job_ids:
        cancel_jobs(job_ids)


def cancel_jobs_per_job_type(job_type: str) -> None:
    query = """SELECT id FROM procrastinate_jobs WHERE (args->>'task') = (aleph.procrastinate.tasks.%s)"""
    job_ids = get_job_ids_by_criteria(query, job_type)
    if job_ids:
        cancel_jobs(job_ids)


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
