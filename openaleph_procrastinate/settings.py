from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from openaleph_procrastinate.legacy import env


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

    ingest_queue: str = "ingest"
    ingest_task: str = "ingestors.tasks.ingest"
    analyze_queue: str = "ftm-analyze"
    analyze_task: str = "ftm_analyze.tasks.analyze"
    index_queue: str = "openaleph-index"
    index_task: str = "aleph.procrastinate.tasks.index_bulk"
    transcribe_queue: str = "ftm-transcribe"
    transcribe_task: str = "ftm_transcribe.tasks.transcribe"
    geocode_queue: str = "ftm-geocode"
    geocode_task: str = "ftm_geocode.tasks.geocode"
    assets_queue: str = "ftm-assets"
    assets_task: str = "ftm_assets.tasks.resolve"


class OpenAlephSettings(DeferSettings):
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
