"""
This is temporary and should use the procrastinate Django models at one point in
the future
"""

from datetime import datetime
from typing import Any, Generator, LiteralString, TypeAlias

import psycopg
from anystore.functools import weakref_cache as cache
from anystore.logging import get_logger
from anystore.util import Took, mask_uri
from psycopg.errors import UndefinedTable

from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.manage import sql
from openaleph_procrastinate.model import AnyJob, DatasetJob, EntityJob, Status
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.tasks import unpack_job

RowType: TypeAlias = str | int | datetime | dict[str, Any]
Rows: TypeAlias = Generator[tuple[RowType, ...], None, None]
Jobs: TypeAlias = Generator[AnyJob | EntityJob, None, None]


class Db:
    """Get a db manager object for the current procrastinate database uri"""

    def __init__(self, uri: str | None = None) -> None:
        self.settings = OpenAlephSettings()
        if self.settings.in_memory_db:
            raise RuntimeError("Can't use in-memory database")
        self.uri = uri or self.settings.procrastinate_db_uri
        self.log = get_logger(__name__, uri=mask_uri(self.uri))

    def configure(self) -> None:
        """Create procrastinate tables and schema (if not exists) and add our
        index optimizations (if not exists)"""
        if self.settings.in_memory_db:
            return
        app = make_app(sync=True)
        with app.open():
            if not app.check_connection():
                self.log.info("Configuring procrastinate database schema ...")
                app.schema_manager.apply_schema()
        self.log.info("Configuring indexes and generated fields ...")
        with Took() as t:
            self._execute(sql.GENERATED_FIELDS)
            self._execute(sql.INDEXES)
            self.log.info("Configuring done.", took=t.took)

    def iterate_status(
        self,
        dataset: str | None = None,
        batch: str | None = None,
        queue: str | None = None,
        task: str | None = None,
        status: Status | None = None,
        active_only: bool | None = True,
    ) -> Rows:
        """
        Iterate through aggregated job status summary

        Each row is an aggregation over
        `dataset,batch,queue_name,task_name,status` and includes jobs count,
        timestamp first event, timestamp last event

        Args:
            dataset: The dataset to filter for
            batch: The job batch to filter for
            queue: The queue name to filter for
            task: The task name to filter for
            status: The status to filter for
            active_only: Only include "active" datasets (at least 1 job in
                'todo' or 'doing')

        Yields:
            Rows a tuple with the fields in this order:
                dataset, batch, queue_name, task_name, status, jobs count,
                timestamp first event, timestamp last event
        """
        if active_only:
            query = sql.STATUS_SUMMARY_ACTIVE
        else:
            query = sql.STATUS_SUMMARY
        yield from self._execute_iter(
            query,
            dataset=dataset,
            batch=batch,
            queue=queue,
            task=task,
            status=status,
        )

    def iterate_jobs(
        self,
        dataset: str | None = None,
        batch: str | None = None,
        queue: str | None = None,
        task: str | None = None,
        status: Status | None = None,
        min_ts: datetime | None = None,
        max_ts: datetime | None = None,
        flatten_entities: bool | None = False,
    ) -> Jobs:
        """
        Iterate job objects from the database by given criteria.

        Args:
            dataset: The dataset to filter for
            batch: The job batch to filter for
            queue: The queue name to filter for
            task: The task name to filter for
            status: The status to filter for
            min_ts: Start timestamp (earliest event found in `procrastinate_events`)
            max_ts: End timestamp (latest event found in `procrastinate_events`)
            flatten_entities: If true, yield a job for each entity found in the source job

        Yields:
            Iterator of [Job][openaleph_procrastinate.model.Job]
        """

        min_ts = min_ts or datetime(1970, 1, 1)
        max_ts = max_ts or datetime.now()
        params = {
            "dataset": dataset,
            "min_ts": min_ts.isoformat(),
            "max_ts": max_ts.isoformat(),
            "batch": batch,
            "queue": queue,
            "task": task,
            "status": status,
        }
        for id, status_, data in self._execute_iter(sql.ALL_JOBS, **params):
            data["id"] = id
            data["status"] = status_
            job = unpack_job(data)
            if flatten_entities and isinstance(job, DatasetJob):
                has_entities = False
                for entity in job.get_entities():
                    if entity.id:
                        has_entities = True
                        yield EntityJob(**data, entity_id=entity.id)
                if not has_entities:
                    yield job
            else:
                yield job

    def cancel_jobs(
        self,
        dataset: str | None = None,
        batch: str | None = None,
        queue: str | None = None,
        task: str | None = None,
    ) -> None:
        """
        Cancel jobs by given criteria.

        Args:
            dataset: The dataset to filter for
            batch: The job batch to filter for
            queue: The queue name to filter for
            task: The task name to filter for
        """

        self._execute(
            sql.CANCEL_JOBS, dataset=dataset, batch=batch, queue=queue, task=task
        )

    def _execute_iter(self, q: LiteralString, **params: str | None) -> Rows:
        with psycopg.connect(self.settings.procrastinate_db_uri) as connection:
            with connection.cursor() as cursor:
                cursor.execute(q, dict(params))
                while rows := cursor.fetchmany(100_000):
                    yield from rows

    def _execute(self, q: LiteralString, **params: str | None) -> None:
        with psycopg.connect(self.settings.procrastinate_db_uri) as connection:
            with connection.cursor() as cursor:
                for query in q.split(";"):
                    cursor.execute(query, dict(params))

    def _destroy(self) -> None:
        """Destroy all data (used in tests)"""
        self.log.warning("🔥 Deleting all procrastinate data 🔥")
        for table in (
            "procrastinate_jobs",
            "procrastinate_workers",
            "procrastinate_events",
        ):
            try:
                self._execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")
            except UndefinedTable:
                pass


@cache
def get_db(uri: str | None = None) -> Db:
    """Get a globally cached `db` instance"""
    settings = OpenAlephSettings()
    uri = uri or settings.procrastinate_db_uri
    return Db(uri)
