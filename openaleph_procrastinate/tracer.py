"""
Simple, quick & dirty tracer module to track task status for entities in a
shared redis instance. This is useful to share task status across services for
quick lookup (psql would be too expensive), e.g. to show a loading spinner in
the UI if something is processing. This module currently is a quick shot to
solve the status lookup for specific queues, it should be refactored at one
point into a more general tracer module that e.g. can also store processing
exceptions in postgres. For this, creating a better class-based queue system and
merge the tracing into it should be considered.

The tracer is used in the @task decorator (middleware) when tracer_uri=... is set
in the kwargs. e.g.:

```python
@task(queue="my-queue", tracer_uri="redis://localhost")
def process(job) -> None:
    pass
```

(See test suite for example)

The tracer backend accepts any uri (sql, file-like, ...), but it is preferable
to use redis for performance reasons.
"""

from functools import cache
from typing import Any, cast

from anystore.fs.redis import RedisFileSystem
from anystore.logging import get_logger
from anystore.store import get_store
from anystore.types import Uri
from anystore.util import join_relpaths

from openaleph_procrastinate.model import DatasetJob, Status
from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)


class Tracer:
    def __init__(
        self, dataset: str, queue: str, task: str, uri: Uri | None = None
    ) -> None:
        if uri is None:
            settings = OpenAlephSettings()
            uri = settings.redis_url
        self._store = get_store(uri, raise_on_nonexist=False)
        self._is_redis = isinstance(self._store._fs, RedisFileSystem)
        if not self._is_redis and not str(self._store.uri).startswith("memory:"):
            log.warn(f"Tracer should use Redis for performance, not `{uri}`")
        self.dataset = dataset
        self.queue = queue
        self.task = task

    def _make_key(self, *parts: str) -> str:
        return join_relpaths(
            "openaleph-procrastinate",
            "tracer",
            self.dataset,
            self.queue,
            self.task,
            *parts,
        )

    def mark(self, entity_id: str, status: Status) -> None:
        """Mark an entity status for the given queue and task. If status is
        'succeeded' remove the data from the tracer."""
        key = self._make_key(entity_id)
        if status == "succeeded":
            return self._store.delete(key, ignore_errors=True)
        self._store.put(key, status)

    def add(self, entity_id: str) -> None:
        """Mark as todo"""
        self.mark(entity_id, "todo")

    def start(self, entity_id: str) -> None:
        """Mark as doing"""
        self.mark(entity_id, "doing")

    def finish(self, entity_id: str) -> None:
        """Mark done which is actually popping (deleting) from the tracer"""
        self.mark(entity_id, "succeeded")

    def is_processing(self, entity_id: str) -> bool:
        """Check if a task for the entity_id is either pending or doing"""
        key = self._make_key(entity_id)
        if not self._store.exists(key):
            return False
        status = self._store.get(key)
        return status in ("todo", "doing")

    def set(self, key: str, value: Any) -> None:
        key = self._make_key(key)
        self._store.put(key, value)

    def get(self, key: str) -> Any:
        key = self._make_key(key)
        return self._store.get(key)

    def incr(self, key: str, value: int) -> int:
        """Increment a counter and return its new value. Atomic on redis."""
        if self._is_redis:
            fs = cast(RedisFileSystem, self._store._fs)
            # `INCR` bypasses the store, so it needs the full backend key
            fs_key = self._store._keys.to_fs_key(self._make_key(key))
            return int(fs._con.incr(fs_key, value))
        value = (self.get(key) or 0) + value
        self.set(key, value)
        return value


@cache
def get_tracer(dataset: str, queue: str, task: str, uri: Uri | None) -> Tracer:
    return Tracer(dataset, queue, task, uri)


def get_job_tracer(job: DatasetJob, uri: str) -> Tracer:
    return get_tracer(job.dataset, job.queue, job.task, uri)
