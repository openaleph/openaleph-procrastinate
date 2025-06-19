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
"""

from typing import Any, Iterable

from followthemoney.proxy import EntityProxy

from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.settings import DeferSettings

settings = DeferSettings()


def ingest(dataset: str, entity: EntityProxy, **context: Any) -> DatasetJob:
    """
    Make a new job for `ingest-file`

    Args:
        dataset: The ftm dataset or collection
        entity: The file or directory entity to ingest
        context: Additional job context
    """
    return DatasetJob.from_entity(
        dataset=dataset,
        queue=settings.ingest_queue,
        task=settings.ingest_task,
        entity=entity,
        **context,
    )


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
        queue=settings.analyze_queue,
        task=settings.analyze_task,
        entities=entities,
        dehydrate=True,
        **context,
    )


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
        queue=settings.index_queue,
        task=settings.index_task,
        entities=entities,
        dehydrate=True,
        **context,
    )


def transcribe(dataset: str, entity: EntityProxy, **context: Any) -> DatasetJob:
    """
    Make a new job for `ftm-transcribe`

    Args:
        dataset: The ftm dataset or collection
        entity: The file entity to ingest
        context: Additional job context
    """
    return DatasetJob.from_entity(
        dataset=dataset,
        queue=settings.transcribe_queue,
        task=settings.transcribe_task,
        entity=entity,
        **context,
    )


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
        queue=settings.geocode_queue,
        task=settings.geocode_task,
        entities=entities,
        **context,
    )


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
        queue=settings.assets_queue,
        task=settings.assets_task,
        entities=entities,
        **context,
    )
