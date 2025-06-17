"""
Known stages to defer jobs to within the OpenAleph stack.

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

INGEST_QUEUE = "ingest-file"
INGEST_TASK = "ingestors.tasks.ingest"


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
        queue=INGEST_QUEUE,
        task=INGEST_TASK,
        entity=entity,
        **context,
    )


ANALYZE_QUEUE = "ftm-analyze"
ANALYZE_TASK = "ftm_analyze.tasks.analyze"


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
        queue=ANALYZE_QUEUE,
        task=ANALYZE_TASK,
        entities=entities,
        dehydrate=True,
        **context,
    )


INDEX_QUEUE = "openaleph"
INDEX_TASK = "aleph.procrastinate.index"


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
        queue=INDEX_QUEUE,
        task=INDEX_TASK,
        entities=entities,
        dehydrate=True,
        **context,
    )


TRANSCRIBE_QUEUE = "ftm-transcribe"
TRANSCRIBE_TASK = "ftm_transcribe.tasks.transcribe"


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
        queue=TRANSCRIBE_QUEUE,
        task=TRANSCRIBE_TASK,
        entity=entity,
        **context,
    )


GEOCODE_QUEUE = "ftm-geocode"
GEOCODE_TASK = "ftm_geocode.tasks.geocode"


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
        queue=GEOCODE_QUEUE,
        task=GEOCODE_TASK,
        entities=entities,
        **context,
    )
