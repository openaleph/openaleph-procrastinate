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
from banal import ensure_dict

from openaleph_procrastinate.model import DatasetJob, Job
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


def reindex(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to reindex into OpenAleph
    It will only deferred if `OPENALEPH_REINDEX_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.reindex.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.reindex.queue,
            task=settings.reindex.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def xref(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to xref into OpenAleph
    It will only deferred if `OPENALEPH_XREF_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.xref.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.xref.queue,
            task=settings.xref.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def load_mapping(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to load_mapping into OpenAleph
    It will only deferred if `OPENALEPH_LOAD_MAPPING_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.load_mapping.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.load_mapping.queue,
            task=settings.load_mapping.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def flush_mapping(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to flush_mapping into OpenAleph
    It will only deferred if `OPENALEPH_FLUSH_MAPPING_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.flush_mapping.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.flush_mapping.queue,
            task=settings.flush_mapping.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def export_search(
    app: App, **context: Any
) -> None:
    """
    Defer a new job to export_search into OpenAleph
    It will only deferred if `OPENALEPH_EXPORT_SEARCH_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        context: Additional job context
    """
    if settings.export_search.defer:
        job = Job(
            queue=settings.export_search.queue,
            task=settings.export_search.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def export_xref(app: App, **context: Any) -> None:
    """
    Defer a new job to export_xref into OpenAleph
    It will only deferred if `OPENALEPH_EXPORT_XREF_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        context: Additional job context
    """
    if settings.export_xref.defer:
        job = DatasetJob(
            dataset="",
            queue=settings.export_xref.queue,
            task=settings.export_xref.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def update_entity(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to update_entity into OpenAleph
    It will only deferred if `OPENALEPH_UPDATE_ENTITY_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.update_entity.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.update_entity.queue,
            task=settings.update_entity.task,
            payload={"context": ensure_dict(context)},
        )
        job.defer(app=app)


def prune_entity(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to prune_entity into OpenAleph
    It will only deferred if `OPENALEPH_PRUNE_ENTITY_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if settings.prune_entity.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=settings.prune_entity.queue,
            task=settings.prune_entity.task,
            payload={"context": ensure_dict(context)},
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
