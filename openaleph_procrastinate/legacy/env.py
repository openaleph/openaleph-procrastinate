"""
Backwards compatibility to Aleph env vars, partly inlined from `aleph.settings`
and `servicelayer.settings`
"""

from os import environ

from banal.bools import as_bool


def env_get(name, default=None):
    value = environ.get(name)
    if value is not None:
        return str(value)
    if default is not None:
        return str(default)


def env_to_int(name, default=0):
    """Extract an integer from the environment."""
    try:
        return int(env_get(name) or 0)
    except (TypeError, ValueError):
        return default


def env_to_bool(name, default=False):
    """Extract a boolean value from the environment consistently."""
    return as_bool(env_get(name), default=default)


##############################################################################
# BASE #

# Show error messages to the user.
DEBUG = env_to_bool("ALEPH_DEBUG", False)
# General instance information
APP_NAME = env_get("ALEPH_APP_NAME", "openaleph")

##############################################################################
# E-MAIL SETTINGS #

MAIL_FROM = env_get("ALEPH_MAIL_FROM", "aleph@domain.com")
MAIL_SERVER = env_get("ALEPH_MAIL_HOST", "localhost")
MAIL_USERNAME = env_get("ALEPH_MAIL_USERNAME")
MAIL_PASSWORD = env_get("ALEPH_MAIL_PASSWORD")
MAIL_USE_SSL = env_to_bool("ALEPH_MAIL_SSL", False)
MAIL_USE_TLS = env_to_bool("ALEPH_MAIL_TLS", True)
MAIL_PORT = env_to_int("ALEPH_MAIL_PORT", 465)
MAIL_DEBUG = env_to_bool("ALEPH_MAIL_DEBUG", DEBUG)

###############################################################################
# DATABASE #

DEFAULT_OPENALEPH_DB_URI = env_get("OPENALEPH_DB_URI") or "postgresql:///openaleph"
DATABASE_URI = env_get("ALEPH_DATABASE_URI") or DEFAULT_OPENALEPH_DB_URI
FTM_STORE_URI = env_get("FTM_STORE_URI") or DATABASE_URI

###############################################################################
# ARCHIVE #

# Amazon client credentials
AWS_KEY_ID = env_get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = env_get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = env_get("AWS_REGION", "eu-west-1")
# S3 compatible Minio host if using Minio for storage
ARCHIVE_ENDPOINT_URL = env_get("ARCHIVE_ENDPOINT_URL")

# Storage type (either 's3', 'gs', or 'file', i.e. local file system):
ARCHIVE_TYPE = env_get("ARCHIVE_TYPE", "file")
ARCHIVE_BUCKET = env_get("ARCHIVE_BUCKET")
ARCHIVE_PATH = env_get("ARCHIVE_PATH")
PUBLICATION_BUCKET = env_get("PUBLICATION_BUCKET", ARCHIVE_BUCKET)

###############################################################################

# Sentry
SENTRY_DSN = env_get("SENTRY_DSN")
SENTRY_ENVIRONMENT = env_get("SENTRY_ENVIRONMENT", "")
SENTRY_RELEASE = env_get("SENTRY_RELEASE", "")

# Instrumentation
PROMETHEUS_ENABLED = env_to_bool("PROMETHEUS_ENABLED", False)
PROMETHEUS_PORT = env_to_int("PROMETHEUS_PORT", 9100)
