from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from openaleph_procrastinate.legacy import env


class ServiceSettings(BaseSettings):
    """
    Settings for a specific service, like `ingest-file` or `ftm-analyze`
    """

    queue: str
    """queue name"""
    task: str
    """task module path"""
    defer: bool = True
    """enable deferring"""


class DeferSettings(BaseSettings):
    """
    Adjust the worker queues and tasks for different stages.

    This is useful e.g. for launching a priority queuing setup for a specific dataset:

    Example:
        ```bash
        # ingest service
        export OPENALEPH_INGEST_QUEUE=ingest-prio-dataset
        export OPENALEPH_ANALYZE_QUEUE=analyze-prio-dataset
        ingestors ingest -d prio_dataset ./documents
        procrastinate worker -q ingest-prio-dataset --one-shot  # stop worker after complete

        # analyze service
        procrastinate worker -q analyze-prio-dataset --one-shot  # stop worker after complete
        ```
    """

    model_config = SettingsConfigDict(
        env_prefix="openaleph_",
        env_nested_delimiter="_",
        env_file=".env",
        nested_model_default_partial_update=True,
        extra="ignore",  # other envs in .env file
    )

    ingest: ServiceSettings = ServiceSettings(
        queue="ingest", task="ingestors.tasks.ingest"
    )
    """ingest-file"""

    analyze: ServiceSettings = ServiceSettings(
        queue="analyze", task="ftm_analyze.tasks.analyze"
    )
    """ftm-analyze"""

    transcribe: ServiceSettings = ServiceSettings(
        queue="transcribe", task="ftm_transcribe.tasks.transcribe"
    )
    """ftm-transcribe"""

    geocode: ServiceSettings = ServiceSettings(
        queue="geocode", task="ftm_geocode.tasks.geocode"
    )
    """ftm-geocode"""

    assets: ServiceSettings = ServiceSettings(
        queue="assets", task="ftm_assets.tasks.resolve"
    )
    """ftm-assets"""

    # OpenAleph

    index: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.index"
    )
    """openaleph indexer"""

    reindex: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.reindex"
    )
    """openaleph reindexer"""

    xref: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.xref"
    )
    """openaleph xref"""

    load_mapping: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.load_mapping"
    )
    """openaleph load_mapping"""

    flush_mapping: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.flush_mapping"
    )
    """openaleph flush_mapping"""

    export_search: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.export_search"
    )
    """openaleph export_search"""

    export_xref: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.export_xref"
    )
    """openaleph export_xref"""

    update_entity: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.update_entity"
    )
    """openaleph update_entity"""

    prune_entity: ServiceSettings = ServiceSettings(
        queue="openaleph", task="aleph.procrastinate.tasks.prune_entity"
    )
    """openaleph update_entity"""


class OpenAlephSettings(BaseSettings):
    """
    `openaleph_procrastinate` settings management using
    [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

    Note:
        All settings can be set via environment variables, prepending
        `OPENALEPH_` (except for those with another alias) via runtime or in a
        `.env` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="openaleph_",
        env_nested_delimiter="_",
        env_file=".env",
        nested_model_default_partial_update=True,
        extra="ignore",  # other envs in .env file
    )

    instance: str = Field(default="openaleph")
    """Instance identifier"""

    debug: bool = Field(default=env.DEBUG, alias="debug")
    """Debug mode"""

    db_uri: str = Field(default=env.DATABASE_URI)
    """OpenAleph database uri"""

    procrastinate_db_uri: str = Field(default=env.DATABASE_URI)
    """Procrastinate database uri, falls back to OpenAleph database uri"""

    ftm_store_uri: str = Field(default=env.FTM_STORE_URI)
    """FollowTheMoney store uri"""
