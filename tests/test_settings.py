"""
Smoke tests for `OpenAlephSettings` subclassed by downstream services.

Downstream apps (e.g. `ingestors`, `ftm-analyze`) subclass `OpenAlephSettings`
and override `env_prefix` for their own settings. In pydantic-settings, the
prefix applies to every field without an explicit alias - including inherited
ones. Inherited settings must keep their canonical environment variable names
regardless of the subclass prefix, so every field on `OpenAlephSettings`
carries an explicit (validation) alias.
"""

from pydantic_settings import SettingsConfigDict

from openaleph_procrastinate.settings import OpenAlephSettings


class DownstreamSettings(OpenAlephSettings):
    """Mimics a downstream service settings class, e.g. `ingestors`"""

    model_config = SettingsConfigDict(
        env_prefix="ingestors_",
        env_file=".env",
        nested_model_default_partial_update=True,
        extra="ignore",
    )

    ocr_languages: str = "eng"
    """A downstream-only setting that should use the subclass prefix"""


# canonical env vars for inherited settings, all set to non-default values
CANONICAL_ENV = {
    "OPENALEPH_INSTANCE": "other-instance",
    "DEBUG": "true",
    "PROCRASTINATE_SYNC": "true",
    "OPENALEPH_DB_URI": "postgresql://canonical/aleph",
    "OPENALEPH_DB_POOL_SIZE": "42",
    "PROCRASTINATE_DB_URI": "postgresql://canonical/procrastinate",
    "FTM_FRAGMENTS_URI": "postgresql://canonical/fragments",
    "REDIS_URL": "redis://canonical:6379/0",
    "OPENALEPH_PROCRASTINATE_DEHYDRATE_ENTITIES": "true",
}

# the same settings remapped to the subclass prefix - these would be read
# (and the canonical ones ignored) if a field lacked an explicit alias
HOSTILE_ENV = {
    "INGESTORS_INSTANCE": "hostile",
    "INGESTORS_DEBUG": "false",
    "INGESTORS_PROCRASTINATE_SYNC": "false",
    "INGESTORS_DB_URI": "postgresql://hostile/aleph",
    "INGESTORS_DB_POOL_SIZE": "99",
    "INGESTORS_PROCRASTINATE_DB_URI": "postgresql://hostile/procrastinate",
    "INGESTORS_FRAGMENTS_URI": "postgresql://hostile/fragments",
    "INGESTORS_REDIS_URL": "redis://hostile:6379/0",
    "INGESTORS_PROCRASTINATE_DEHYDRATE_ENTITIES": "false",
}


def test_settings_fields_have_explicit_alias():
    # the invariant that makes inherited settings immune to subclass prefixes
    for name, field in OpenAlephSettings.model_fields.items():
        assert field.alias or field.validation_alias, (
            f"`{name}` needs an explicit (validation_)alias, otherwise a "
            "subclass overriding `env_prefix` remaps its environment variable"
        )


def test_settings_subclass_reads_canonical_env(monkeypatch):
    for key, value in {**CANONICAL_ENV, **HOSTILE_ENV}.items():
        monkeypatch.setenv(key, value)

    settings = DownstreamSettings(_env_file=None)
    assert settings.instance == "other-instance"
    assert settings.debug is True
    assert settings.procrastinate_sync is True
    assert settings.db_uri == "postgresql://canonical/aleph"
    assert settings.db_pool_size == 42
    assert settings.procrastinate_db_uri == "postgresql://canonical/procrastinate"
    assert settings.fragments_uri == "postgresql://canonical/fragments"
    assert settings.redis_url == "redis://canonical:6379/0"
    assert settings.procrastinate_dehydrate_entities is True

    # downstream settings still use the subclass prefix
    assert settings.ocr_languages == "eng"
    monkeypatch.setenv("INGESTORS_OCR_LANGUAGES", "deu")
    assert DownstreamSettings(_env_file=None).ocr_languages == "deu"


def test_settings_subclass_equals_base(monkeypatch):
    # auto-generate a hostile remapped env var for every inherited field so
    # that fields added in the future are covered as well
    base = OpenAlephSettings(_env_file=None)
    for name in OpenAlephSettings.model_fields:
        value = getattr(base, name)
        if isinstance(value, bool):
            hostile = str(not value).lower()
        elif isinstance(value, int):
            hostile = str(value + 1)
        else:
            hostile = "hostile-value"
        monkeypatch.setenv(f"INGESTORS_{name.upper()}", hostile)

    settings = DownstreamSettings(_env_file=None)
    for name in OpenAlephSettings.model_fields:
        assert getattr(settings, name) == getattr(
            base, name
        ), f"`{name}` is remapped by the subclass `env_prefix`"
