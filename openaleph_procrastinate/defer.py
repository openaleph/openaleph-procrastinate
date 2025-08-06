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

from banal import ensure_dict
from followthemoney.proxy import EntityProxy

from openaleph_procrastinate.app import App
from openaleph_procrastinate.model import DatasetJob, Job
from openaleph_procrastinate.settings import DeferSettings

tasks = DeferSettings()


def get_priority(data: dict[str, Any], default: int) -> int:
    return data.get("priority") or default


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
    if tasks.ingest.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.ingest.queue,
            task=tasks.ingest.task,
            entities=entities,
            **context,
        )
        priority = get_priority(context, tasks.ingest.get_priority())
        job.defer(app, priority)


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
    if tasks.analyze.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.analyze.queue,
            task=tasks.analyze.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        priority = get_priority(context, tasks.analyze.get_priority())
        job.defer(app, priority)


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
    if tasks.index.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.index.queue,
            task=tasks.index.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        priority = get_priority(context, tasks.index.get_priority())
        job.defer(app, priority)


def reindex(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to reindex into OpenAleph
    It will only deferred if `OPENALEPH_REINDEX_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.reindex.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.reindex.queue,
            task=tasks.reindex.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.reindex.get_priority())
        job.defer(app, priority)


def xref(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to xref into OpenAleph
    It will only deferred if `OPENALEPH_XREF_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.xref.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.xref.queue,
            task=tasks.xref.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.xref.get_priority())
        job.defer(app, priority)


def load_mapping(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to load_mapping into OpenAleph
    It will only deferred if `OPENALEPH_LOAD_MAPPING_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.load_mapping.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.load_mapping.queue,
            task=tasks.load_mapping.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.load_mapping.get_priority())
        job.defer(app, priority)


def flush_mapping(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to flush_mapping into OpenAleph
    It will only deferred if `OPENALEPH_FLUSH_MAPPING_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.flush_mapping.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.flush_mapping.queue,
            task=tasks.flush_mapping.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.flush_mapping.get_priority())
        job.defer(app, priority)


def export_search(app: App, **context: Any) -> None:
    """
    Defer a new job to export_search into OpenAleph
    It will only deferred if `OPENALEPH_EXPORT_SEARCH_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        context: Additional job context
    """
    if tasks.export_search.defer:
        job = Job(
            queue=tasks.export_search.queue,
            task=tasks.export_search.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.export_search.get_priority())
        job.defer(app, priority)


def export_xref(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to export_xref into OpenAleph
    It will only deferred if `OPENALEPH_EXPORT_XREF_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        context: Additional job context
    """
    if tasks.export_xref.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.export_xref.queue,
            task=tasks.export_xref.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.export_xref.get_priority())
        job.defer(app, priority)


def update_entity(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to update_entity into OpenAleph
    It will only deferred if `OPENALEPH_UPDATE_ENTITY_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.update_entity.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.update_entity.queue,
            task=tasks.update_entity.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.update_entity.get_priority())
        job.defer(app, priority)


def prune_entity(app: App, dataset: str, **context: Any) -> None:
    """
    Defer a new job to prune_entity into OpenAleph
    It will only deferred if `OPENALEPH_PRUNE_ENTITY_DEFER=1` (the default)

    Args:
        app: The procrastinate app instance
        dataset: The ftm dataset or collection
        context: Additional job context
    """
    if tasks.prune_entity.defer:
        job = DatasetJob(
            dataset=dataset,
            queue=tasks.prune_entity.queue,
            task=tasks.prune_entity.task,
            payload={"context": ensure_dict(context)},
        )
        priority = get_priority(context, tasks.prune_entity.get_priority())
        job.defer(app, priority)


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
    if tasks.transcribe.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.transcribe.queue,
            task=tasks.transcribe.task,
            entities=entities,
            dehydrate=True,
            **context,
        )
        priority = get_priority(context, tasks.transcribe.get_priority())
        job.defer(app, priority)


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
    if tasks.geocode.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.geocode.queue,
            task=tasks.geocode.task,
            entities=entities,
            **context,
        )
        priority = get_priority(context, tasks.geocode.get_priority())
        job.defer(app, priority)


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
    if tasks.assets.defer:
        job = DatasetJob.from_entities(
            dataset=dataset,
            queue=tasks.assets.queue,
            task=tasks.assets.task,
            entities=entities,
            **context,
        )
        priority = get_priority(context, tasks.assets.get_priority())
        job.defer(app, priority)
