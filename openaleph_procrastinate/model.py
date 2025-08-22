import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ContextManager, Generator, Iterable, Literal, Self, TypeAlias

from anystore.logging import BoundLogger, get_logger
from anystore.store.virtual import VirtualIO
from anystore.util import clean_dict
from banal import ensure_dict
from followthemoney import model
from followthemoney.proxy import EntityProxy
from ftmq.store.fragments.loader import BulkLoader
from pydantic import BaseModel, ConfigDict, computed_field

from openaleph_procrastinate import helpers
from openaleph_procrastinate.app import App, run_sync_worker
from openaleph_procrastinate.settings import (
    MAX_PRIORITY,
    MIN_PRIORITY,
    OpenAlephSettings,
)
from openaleph_procrastinate.util import make_checksum_entity

settings = OpenAlephSettings()


def get_priority() -> int:
    return random.randint(MIN_PRIORITY, MAX_PRIORITY)


class EntityFileReference(BaseModel):
    """
    A file reference (via `content_hash`) to a servicelayer file from an entity
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset: str
    content_hash: str
    entity: EntityProxy

    def open(self: Self) -> ContextManager[VirtualIO]:
        """
        Open the file attached to this job
        """
        return helpers.open_file(self.dataset, self.content_hash)

    def get_localpath(self: Self) -> ContextManager[Path]:
        """
        Get a temporary path for the file attached to this job
        """
        return helpers.get_localpath(self.dataset, self.content_hash)


Status = Literal[
    "todo", "doing", "succeeded", "failed", "aborted", "aborting", "cancelled"
]


class JobModel(BaseModel):
    """
    A job with arbitrary payload
    """

    queue: str
    task: str
    payload: dict[str, Any] = {}

    # from procrastinate table:
    id: int | None = None
    status: Status | None = None
    scheduled_at: datetime | None = None


class Job(JobModel):
    """
    A job with arbitrary payload
    """

    @property
    def context(self) -> dict[str, Any]:
        """Get the context from the payload if any"""
        return ensure_dict(self.payload.get("context")) or {}

    @property
    def log(self) -> BoundLogger:
        return get_logger(name="openaleph.job", queue=self.queue, task=self.task)

    def defer(self: Self, app: App, priority: int | None = None) -> None:
        """Defer this job"""
        self.log.debug("Deferring ...", payload=self.payload)
        data = clean_dict(self.model_dump(mode="json"))
        app.configure_task(
            name=self.task, queue=self.queue, priority=priority or get_priority()
        ).defer(**data)
        if settings.debug:
            # option to change synchronousness during test runtime
            _settings = OpenAlephSettings()
            if _settings.procrastinate_sync:
                # run worker synchronously (for testing)
                run_sync_worker(app)


class DatasetJob(Job):
    """
    A job with arbitrary payload bound to a `dataset`.
    The payload always contains an iterable of serialized `EntityProxy` objects
    in the `entities` key. It may contain other payload context data in the
    `context` key.

    There are helpers for accessing archive files or loading entities.
    """

    dataset: str
    batch: str | None = None

    @property
    def log(self) -> BoundLogger:
        return get_logger(
            name=f"openaleph.job.{self.dataset}",
            dataset=self.dataset,
            queue=self.queue,
            task=self.task,
            batch=self.batch,
        )

    def get_writer(self: Self) -> ContextManager[BulkLoader]:
        """Get the writer for the dataset of the current job"""
        return helpers.entity_writer(self.dataset)

    def get_entities(self) -> Generator[EntityProxy, None, None]:
        """
        Get the entities from the payload
        """
        assert "entities" in self.payload, "No entities in payload"
        for data in self.payload["entities"]:
            yield model.get_proxy(data)

    def load_entities(self: Self) -> Generator[EntityProxy, None, None]:
        """Load the entities from the store to refresh it to the latest data"""
        assert "entities" in self.payload, "No entities in payload"
        for data in self.payload["entities"]:
            yield helpers.load_entity(self.dataset, data["id"])

    # Helpers for file jobs that access the servicelayer archive

    def get_file_references(self) -> Generator[EntityFileReference, None, None]:
        """
        Get file references per entity from this job

        Example:
            ```python
            # process temporary file paths
            for reference in job.get_file_references():
                with reference.get_local_path() as path:
                    subprocess.run(["command", "-i", str(path)])
                # temporary path will be cleaned up when leaving context

            # process temporary file handlers
            for reference in job.get_file_references():
                with reference.open() as handler:
                    do_something(handler.read())
                # temporary path will be cleaned up when leaving context
            ```

        Yields:
            The file references
        """
        for entity in self.get_entities():
            for content_hash in entity.get("contentHash", quiet=True):
                yield EntityFileReference(
                    dataset=self.dataset, entity=entity, content_hash=content_hash
                )

    @classmethod
    def from_entities(
        cls,
        dataset: str,
        queue: str,
        task: str,
        entities: Iterable[EntityProxy],
        dehydrate: bool | None = False,
        **context: Any,
    ) -> Self:
        """
        Make a job to process entities for a dataset

        Args:
            dataset: Name of the dataset
            queue: Name of the queue
            task: Python module path of the task
            entities: Entities
            dehydrate: Reduce entity payload to only a reference (tasks should
                re-fetch these entities from the store if they need more data)
            context: Job context
        """
        if dehydrate:
            entities_ = (make_checksum_entity(e, quiet=True) for e in entities)
            entities = (e for e in entities_ if e is not None)
        return cls(
            dataset=dataset,
            queue=queue,
            task=task,
            batch=context.pop("batch", None),
            payload={
                "entities": [e.to_dict() for e in entities],
                "context": ensure_dict(context),
            },
        )


class EntityJob(JobModel):
    dataset: str
    entity_id: str


AnyJob: TypeAlias = Job | DatasetJob


class StatusCounts(BaseModel):
    todo: int = 0
    doing: int = 0
    succeeded: int = 0
    failed: int = 0
    aborted: int = 0
    aborting: int = 0
    cancelled: int = 0

    min_ts: datetime | None = None
    max_ts: datetime | None = None

    @computed_field
    @property
    def remaining_time(self) -> timedelta | None:
        if self.finished and self.min_ts and self.max_ts:
            took = self.max_ts - self.min_ts
            remaining = (took.seconds / self.finished) * self.todo
            return timedelta(seconds=remaining)

    @computed_field
    @property
    def took(self) -> timedelta | None:
        max_ts = self.max_ts or datetime.now(UTC)
        if self.finished and self.min_ts:
            return max_ts - self.min_ts
        if self.min_ts:
            return datetime.now(UTC) - self.min_ts

    @computed_field
    @property
    def total(self) -> int:
        return sum(
            (
                self.todo,
                self.doing,
                self.succeeded,
                self.failed,
                self.aborted,
                self.aborting,
                self.cancelled,
            )
        )

    @computed_field
    @property
    def active(self) -> int:
        return self.todo + self.doing

    @computed_field
    @property
    def finished(self) -> int:
        return self.succeeded + self.failed + self.aborted + self.cancelled

    def is_active(self) -> bool:
        return self.active > 0

    def is_running(self) -> bool:
        return self.doing > 0

    def add_child_stats(self, child: "StatusCounts") -> None:
        self.todo += child.todo
        self.doing += child.doing
        self.succeeded += child.succeeded
        self.failed += child.failed
        self.aborted += child.aborted
        self.cancelled += child.cancelled
        if child.min_ts:
            if not self.min_ts or (self.min_ts and self.min_ts > child.min_ts):
                self.min_ts = child.min_ts
        if child.max_ts:
            if not self.max_ts or (self.max_ts and self.max_ts < child.max_ts):
                self.max_ts = child.max_ts


class TaskStatus(StatusCounts):
    name: str


class QueueStatus(StatusCounts):
    name: str
    tasks: list[TaskStatus] = []


class BatchStatus(StatusCounts):
    name: str
    queues: list[QueueStatus] = []


SYSTEM_DATASET = "__system__"


class DatasetStatus(StatusCounts):
    name: str
    batches: list[BatchStatus] = []

    def is_system(self) -> bool:
        return self.name == SYSTEM_DATASET
