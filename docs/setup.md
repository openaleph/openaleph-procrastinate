# Setup

This guide describes the setup of the `openaleph-procrastinate` app.

## Installation

Install [`openaleph-procrastinate`](https://github.com/openaleph/openaleph-procrastinate) with its requirements:

pip:

    pip install openaleph-procrastinate

poetry:

    poetry add openaleph-procrastinate

This will include all the required dependencies.

## Configuration

!!! info
    For local development or testing, set the environment variable `DEBUG=1` to use an in-memory task backend instead of postgresql.

The **OpenAleph** settings are configured via environment vars via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

For a full list of `openaleph-procrastinate` settings, refer to the [settings reference](./reference/settings.md).

### Database

Set up the environment variable `PROCRASTINATE_DB_URI` which falls back to `OPENALEPH_DB_URI` (default: `postgresql:///openaleph`).

### Initial database setup

    openaleph-procrastinate init-db

### Upgrading an existing database

`init-db` also applies all pending [procrastinate migrations](https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html) to an existing database (tracked in the `openaleph_procrastinate_migrations` table) and re-installs our optimizations afterwards. Concurrent runs (e.g. several services starting at once) wait for each other.

!!! warning
    `pre` and `post` migrations are applied at once, so upgrade all services (and their procrastinate version) together: older procrastinate versions may not work with the migrated database.

!!! info
    Some migrations build indexes `CONCURRENTLY`, so `init-db` may take a while on a big jobs table.
