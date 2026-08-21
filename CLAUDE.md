# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

1. Don’t assume. Don’t hide confusion. Surface tradeoffs.
2. Minimum code that solves the problem. Nothing speculative.
3. Touch only what you must. Clean up only your own mess.
4. Define success criteria. Loop until verified.

## Project Overview

openaleph-procrastinate is a PostgreSQL-backed task queue library for the OpenAleph data investigative platform. It wraps [procrastinate](https://procrastinate.readthedocs.io/) and provides Job models, helpers, and defer utilities for distributed services.

## Development Commands

```bash
# Virtual environment
source .venv/bin/activate       # Always activate before running commands

# Install dependencies (Poetry required)
make install                    # or: poetry install --with dev --all-extras

# Code quality
make lint                       # flake8 checks
make typecheck                  # mypy --strict
make pre-commit                 # Run all pre-commit hooks

# Testing
make test                       # Run all tests with coverage
poetry run pytest tests/ -v     # Run tests verbosely
poetry run pytest tests/test_defer.py -v  # Run single test file
poetry run pytest tests/test_defer.py::test_function -v  # Run single test

# Build / docs
make build                      # Build package
make clean                      # Clean build artifacts
make documentation              # zensical build + sync to S3 (docs/, mkdocs.yml)
```

## Testing Environment

Unit tests (`tests/`) run with these environment variables (set in `[tool.pytest_env]` in pyproject.toml):
- `DEBUG=1`
- `PROCRASTINATE_SYNC=1` - Runs workers synchronously
- `PROCRASTINATE_DB_URI=memory:` - In-memory connector (`procrastinate.testing.InMemoryConnector`)
- `FSSPEC_S3_ENDPOINT_URL=http://localhost:8888` - Mocked S3

Tests use `moto` (session-scoped `ThreadedMotoServer` in `tests/conftest.py`) for S3 mocking.

End-to-end tests (`e2e/`) need a **real PostgreSQL** — they are not run by `make test`. They run the installed CLI, a real `procrastinate worker`, and `e2e/test_e2e.py`:

```bash
cd e2e && PROCRASTINATE_DB_URI=postgresql://... PYTHONPATH=../ bash ./test.sh
```

## Architecture

### Core Components

- **`app.py`** - `App` subclass + `make_app()`; PostgreSQL connection pooling (TTL-cached psycopg pools with health checks, `max_idle`/`max_lifetime`), in-memory connector when the db uri is `memory:`
- **`repository.py`** - `Archive` / `EntityStore` protocols over the legacy stores (servicelayer archive + ftm fragments) and ftm-lakehouse; opt in with `OPENALEPH_LAKEHOUSE=1`. Backends are imported lazily
- **`model.py`** - Pydantic models: `Job`, `DatasetJob`, `EntityJob`, `EntityFileReference`, plus the status aggregates (`StatusCounts`, `TaskStatus`, `QueueStatus`, `BatchStatus`, `DatasetStatus`)
- **`settings.py`** - Configuration via `OPENALEPH_*` environment variables
- **`helpers.py`** - Thin façade over `repository.py` for archive files and entities within jobs
- **`defer.py`** - Convenience functions to defer jobs to pipeline stages (ingest, analyze, index, etc.)
- **`tasks.py`** - `@task` decorator that auto-unpacks JSON payloads to Job models; `Priorities` buckets
- **`tracer.py`** - Optional per-entity status tracking in an anystore store (redis preferred), wired via `@task(..., tracer_uri=...)`
- **`util.py`** - Entity reducers (`make_stub_entity`, `make_file_entity`) and batched Page-fragment lookup
- **`exceptions.py`** - `InvalidJob`, `ArchiveFileNotFound`, and the `ErrorHandler` context manager (re-raises when `DEBUG`)
- **`logging.py`** - Patches procrastinate's job logging to drop full payload reprs and promote dataset/entity summaries to structlog fields
- **`cli.py`** - typer CLI, exposed as the `openaleph-procrastinate` entrypoint
- **`manage/`** - `db.py` (`Db` schema manager: generated `dataset`/`batch`/`created_at`/`updated_at` columns, dropped worker FK, custom prune-stalled-workers function, indexes, optimized fetch function), `sql.py` (SQL constants), `status.py` (job status aggregation)

### Task Conventions

Tasks live in a `tasks` submodule and are referenced as `<library_name>.tasks.<task_name>`:

```python
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import Job
from openaleph_procrastinate.tasks import task

app = make_app(__loader__.name)

@task(app=app)
def my_task(job: Job) -> None:
    # Process job
    new_job = Job(...)
    new_job.defer(app=app)  # Defer follow-up work
```

Extra kwargs pass through to `app.task()` (e.g. `pass_context=True`); `tracer_uri=...` is consumed by the decorator to enable entity status tracing.

### Queue Naming

- Single queue service: use service name (e.g., `ftm-geocode`)
- Multiple queues: prefix with library name, separate with `--` (e.g., `ftm-analyze--mentions`)

### Job Types

- `Job` - Base job with queue, task, payload
- `DatasetJob` - Job bound to a dataset with entity helpers (`get_entities()`, `get_file_references()`)
- `EntityJob` - Single entity processing

### Settings

`OpenAlephSettings` and `DeferSettings` are `pydantic-settings` models with the `openaleph_` env prefix and a `.env` file. Per-stage queue/task/priority defaults live in `DeferSettings` and are overridable per service, e.g. `OPENALEPH_INGEST_QUEUE`, `OPENALEPH_ANALYZE_TASK`, `OPENALEPH_INDEX_DEFER=0`.

### Running Workers

```bash
export PROCRASTINATE_APP=<library_name>.tasks.app
procrastinate worker -q <queue-name>
```

### CLI

```bash
openaleph-procrastinate init-db          # Apply procrastinate schema + our optimizations
openaleph-procrastinate ensure-indexes   # Reconcile custom indexes (--force to recreate)
openaleph-procrastinate defer-jobs -i jobs.json
openaleph-procrastinate defer-entities -i entities.json -d <dataset> -q <queue> -t <task>
openaleph-procrastinate requeue-failed [-d dataset] [-q queue] [-t task]
openaleph-procrastinate requeue-stalled [-d dataset] [-q queue] [-t task]
```

## Key Dependencies

- `procrastinate` - PostgreSQL task queue
- `followthemoney` / `ftmq` / `ftm-lakehouse` - Entity model and stores
- `openaleph-servicelayer` - Legacy archive backend
- `anystore` - Store/URI abstraction, logging, CLI error handling
- `pydantic` / `pydantic-settings` - Data validation and configuration
- `psycopg` / `psycopg-pool` - PostgreSQL driver with connection pooling
- `typer` (via `anystore`) - CLI
