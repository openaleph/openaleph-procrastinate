"""
Known stages to defer jobs to within the OpenAleph stack.

See [Settings][openaleph_procrastinate.settings.DeferSettings]
for configuring queue names and tasks.

Example:
    ```python
    from openaleph_procrastinate import defer

    @task(app=app)
    def analyze(job: DatasetJob) -> Defers:
        result = analyze_entities(job.load_entities())
        # defer to index stage
        yield defer.index(job.dataset, result)
    ```

To disable deferring for a service, use environment variable:

For example, to disable indexing entities after ingestion, start the
`ingest-file` worker with this config: `OPENALEPH_INDEX_DEFER=0`
"""

import functools
from typing import Any, Callable, Iterable

from followthemoney.proxy import EntityProxy

from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.settings import DeferSettings

settings = DeferSettings()


def check_defer(
    func: Callable[..., DatasetJob] | None = None, enabled: bool | None = True
) -> Callable[..., Any]:
    def _decorator(func):
        @functools.wraps(func)
        def _inner(*args, **kwargs):
            job = func(*args, **kwargs)
            if enabled:
                return job
            job.log.info(f"Not deferring to `{job.task}` (deferring disabled)")

        return _inner

    if func is None:
        return _decorator
    return _decorator(func)


@check_defer(enabled=settings.ingest.defer)
def ingest(dataset: str, entities: Iterable[EntityProxy], **context: Any) -> DatasetJob:
    """
    Make a new job for `ingest-file`

    Args:
        dataset: The ftm dataset or collection
        entities: The file or directory entities to ingest
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.ingest.queue,
        task=settings.ingest.task,
        entities=entities,
        **context,
    )


@check_defer(enabled=settings.analyze.defer)
def analyze(
    dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> DatasetJob:
    """
    Make a new job for `ftm-analyze`

    Args:
        dataset: The ftm dataset or collection
        entities: The entities to analyze
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.analyze.queue,
        task=settings.analyze.task,
        entities=entities,
        dehydrate=True,
        **context,
    )


@check_defer(enabled=settings.index.defer)
def index(dataset: str, entities: Iterable[EntityProxy], **context: Any) -> DatasetJob:
    """
    Make a new job to index into OpenAleph

    Args:
        dataset: The ftm dataset or collection
        entities: The entities to index
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.index.queue,
        task=settings.index.task,
        entities=entities,
        dehydrate=True,
        **context,
    )


@check_defer(enabled=settings.transcribe.defer)
def transcribe(
    dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> DatasetJob:
    """
    Make a new job for `ftm-transcribe`

    Args:
        dataset: The ftm dataset or collection
        entity: The file entity to ingest
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.transcribe.queue,
        task=settings.transcribe.task,
        entities=entities,
        **context,
    )


@check_defer(enabled=settings.geocode.defer)
def geocode(
    dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> DatasetJob:
    """
    Make a new job for `ftm-geocode`

    Args:
        dataset: The ftm dataset or collection
        entities: The entities to geocode
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.geocode.queue,
        task=settings.geocode.task,
        entities=entities,
        **context,
    )


@check_defer(enabled=settings.assets.defer)
def resolve_assets(
    dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> DatasetJob:
    """
    Make a new job for `ftm-assets`

    Args:
        dataset: The ftm dataset or collection
        entities: The entities to resolve assets for
        context: Additional job context
    """
    return DatasetJob.from_entities(
        dataset=dataset,
        queue=settings.assets.queue,
        task=settings.assets.task,
        entities=entities,
        **context,
    )
