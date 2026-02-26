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
@task(queue="my-queue", trace_uri="redis://localhost")
def process(job) -> None:
    pass
```

(See test suite for example)

The tracer backend accepts any uri (sql, file-like, ...), but it is preferable
to use redis for performance reasons.
"""

from functools import cache

from anystore.store import get_store
from anystore.types import Uri
from anystore.util import join_relpaths

from openaleph_procrastinate.model import Status
from openaleph_procrastinate.settings import OpenAlephSettings


class Tracer:
    def __init__(self, queue: str, task: str, uri: Uri | None = None) -> None:
        if uri is None:
            settings = OpenAlephSettings()
            uri = settings.redis_uri
        self._store = get_store(uri or "memory://")
        self.queue = queue
        self.task = task

    def _make_key(self, entity_id: str) -> str:
        return join_relpaths(
            "openaleph-procrastinate", "tracer", self.queue, self.task, entity_id
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


@cache
def get_tracer(queue: str, task: str, uri: Uri | None) -> Tracer:
    return Tracer(queue, task, uri)
