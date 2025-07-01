"""
Known stages to defer jobs to within the OpenAleph stack.

See [Settings][openaleph_procrastinate.settings.DeferSettings]
for configuring queue names and tasks.

Conventions / common pattern: Tasks are responsible to explicitly defer
following tasks. This defer call is not conditional but happens always, but
actually deferring happens in this module and is depending on runtime settings
(see below).

Example:
    ```python
    from openaleph_procrastinate import defer

    @task(app=app)
    def analyze(job: DatasetJob) -> None:
        result = analyze_entities(job.load_entities())
        # defer to index stage
        defer.index(app, job.dataset, result)
    ```

To disable deferring for a service, use environment variable:

For example, to disable indexing entities after ingestion, start the
`ingest-file` worker with this config: `OPENALEPH_INDEX_DEFER=0`
"""

from typing import Any, Iterable

from followthemoney.proxy import EntityProxy
from procrastinate import App

from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.settings import DeferSettings

settings = DeferSettings()


def ingest(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job for `ingest-file`.
    It will only deferred if `OPENALEPH_INGEST_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The file or directory entities to ingest
        context: Additional job context
    """
    if settings.ingest.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.ingest.queue,
            task=settings.ingest.task,
            entities=entities,
            **context,
        )
        job.defer(app)


def analyze(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job for `ftm-analyze`
    It will only deferred if `OPENALEPH_ANALYZE_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The entities to analyze
        context: Additional job context
    """
    if settings.analyze.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.analyze.queue,
            task=settings.analyze.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        job.defer(app=app)


def index(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job to index into OpenAleph
    It will only deferred if `OPENALEPH_INDEX_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The entities to index
        context: Additional job context
    """
    if settings.index.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.index.queue,
            task=settings.index.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        job.defer(app=app)


def transcribe(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job for `ftm-transcribe`
    It will only deferred if `OPENALEPH_TRANSCRIBE_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The file entities to ingest
        context: Additional job context
    """
    if settings.transcribe.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.transcribe.queue,
            task=settings.transcribe.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        job.defer(app=app)


def geocode(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job for `ftm-geocode`
    It will only deferred if `OPENALEPH_GEOCODE_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The entities to geocode
        context: Additional job context
    """
    if settings.geocode.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.geocode.queue,
            task=settings.geocode.task,
            entities=entities,
            **context,
        )
        job.defer(app=app)


def resolve_assets(
    app: App, dataset: str, entities: Iterable[EntityProxy], **context: Any
) -> None:
    """
    Defer a new job for `ftm-assets`
    It will only deferred if `OPENALEPH_ASSETS_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        entities: The entities to resolve assets for
        context: Additional job context
    """
    if settings.assets.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=settings.assets.queue,
            task=settings.assets.task,
            entities=entities,
            **context,
        )
        job.defer(app=app)
