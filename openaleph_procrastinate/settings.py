from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from openaleph_procrastinate.legacy import env


class OpenAlephSettings(BaseSettings):
    """
    `openaleph_procrastinate` settings management using
    [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

    Note:
        All settings can be set via environment variables in uppercase,
        prepending `OPENALEPH_` (except for those with another alias) via
        runtime or in a `.env` file.
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
