"""
Backwards compatibility to Aleph env vars, partly inlined from `aleph.settings`
and `servicelayer.settings`
"""

from servicelayer import env

##############################################################################
# BASE #

# Show error messages to the user.
DEBUG = env.to_bool("ALEPH_DEBUG", False)
# General instance information
APP_NAME = env.get("ALEPH_APP_NAME", "openaleph")

##############################################################################
# E-MAIL SETTINGS #

MAIL_FROM = env.get("ALEPH_MAIL_FROM", "aleph@domain.com")
MAIL_SERVER = env.get("ALEPH_MAIL_HOST", "localhost")
MAIL_USERNAME = env.get("ALEPH_MAIL_USERNAME")
MAIL_PASSWORD = env.get("ALEPH_MAIL_PASSWORD")
MAIL_USE_SSL = env.to_bool("ALEPH_MAIL_SSL", False)
MAIL_USE_TLS = env.to_bool("ALEPH_MAIL_TLS", True)
MAIL_PORT = env.to_int("ALEPH_MAIL_PORT", 465)
MAIL_DEBUG = env.to_bool("ALEPH_MAIL_DEBUG", DEBUG)

###############################################################################
# DATABASE #

DEFAULT_OPENALEPH_DB_URI = "postgresql:///openaleph"
DATABASE_URI = env.get("ALEPH_DATABASE_URI") or DEFAULT_OPENALEPH_DB_URI
FTM_STORE_URI = env.get("FTM_STORE_URI") or DATABASE_URI

###############################################################################
# ARCHIVE #

# Amazon client credentials
AWS_KEY_ID = env.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = env.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = env.get("AWS_REGION", "eu-west-1")
# S3 compatible Minio host if using Minio for storage
ARCHIVE_ENDPOINT_URL = env.get("ARCHIVE_ENDPOINT_URL")

# Storage type (either 's3', 'gs', or 'file', i.e. local file system):
ARCHIVE_TYPE = env.get("ARCHIVE_TYPE", "file")
ARCHIVE_BUCKET = env.get("ARCHIVE_BUCKET")
ARCHIVE_PATH = env.get("ARCHIVE_PATH")
PUBLICATION_BUCKET = env.get("PUBLICATION_BUCKET", ARCHIVE_BUCKET)

###############################################################################

# Sentry
SENTRY_DSN = env.get("SENTRY_DSN")
SENTRY_ENVIRONMENT = env.get("SENTRY_ENVIRONMENT", "")
SENTRY_RELEASE = env.get("SENTRY_RELEASE", "")

# Instrumentation
PROMETHEUS_ENABLED = env.to_bool("PROMETHEUS_ENABLED", False)
PROMETHEUS_PORT = env.to_int("PROMETHEUS_PORT", 9100)
