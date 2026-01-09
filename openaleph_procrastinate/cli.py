from typing import Annotated, Optional

import typer
from anystore.cli import ErrorHandler
from anystore.io import logged_items, smart_stream_json
from anystore.logging import configure_logging, get_logger
from ftmq.io import smart_read_proxies
from rich import print

from openaleph_procrastinate import __version__, model, tasks
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.manage.db import get_db
from openaleph_procrastinate.settings import OpenAlephSettings

settings = OpenAlephSettings()

cli = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=settings.debug)
log = get_logger(__name__)

DEFAULT_QUEUE = "default"

OPT_INPUT_URI = typer.Option("-", "-i", help="Input uri, default stdin")
OPT_DATASET = typer.Option(..., "-d", help="Dataset")
OPT_QUEUE = typer.Option(DEFAULT_QUEUE, "-q", help="Queue name")
OPT_TASK = typer.Option(..., "-t", help="Task module path")


@cli.callback(invoke_without_command=True)
def cli_opal_procrastinate(
    version: Annotated[Optional[bool], typer.Option(..., help="Show version")] = False,
    settings: Annotated[
        Optional[bool], typer.Option(..., help="Show current settings")
    ] = False,
):
    if version:
        print(__version__)
        raise typer.Exit()
    if settings:
        settings_ = OpenAlephSettings()
        print(settings_)
        raise typer.Exit()
    configure_logging()


@cli.command()
def defer_entities(
    input_uri: str = OPT_INPUT_URI,
    dataset: str = OPT_DATASET,
    queue: str = OPT_QUEUE,
    task: str = OPT_TASK,
):
    """
    Defer jobs for a stream of proxies
    """
    app = make_app()
    with ErrorHandler(log), app.open():
        for proxy in smart_read_proxies(input_uri):
            job = model.DatasetJob.from_entities(
                dataset=dataset, queue=queue, task=task, entities=[proxy]
            )
            job.defer(app)


@cli.command()
def defer_jobs(input_uri: str = OPT_INPUT_URI):
    """
    Defer jobs from an input json stream
    """
    app = make_app()
    with ErrorHandler(log), app.open():
        for data in smart_stream_json(input_uri):
            job = tasks.unpack_job(data)
            job.defer(app)


@cli.command()
def init_db():
    """Initialize procrastinate database schema"""
    with ErrorHandler(log):
        if settings.in_memory_db:
            return
        db = get_db()
        db.configure()


@cli.command()
def requeue_failed(
    dataset: str = OPT_DATASET,
    queue: str = OPT_QUEUE,
    task: str = OPT_TASK,
):
    """
    Requeue failed jobs matching the given filters.

    This command finds all jobs with status='failed' that match the optional filters
    (dataset, queue, task) and retries them by setting their status back to 'todo'.
    """
    from procrastinate import utils

    with ErrorHandler(log):
        if settings.in_memory_db:
            log.error("Cannot requeue jobs with in-memory database")
            raise typer.Exit(1)

        db = get_db()
        app = make_app(sync=True)

        # Get failed jobs logging iterator
        failed_jobs = logged_items(
            db.get_failed_jobs(
                dataset=dataset,
                queue=queue,
                task=task,
            ),
            "Requeuing",
            1000,
            "Job",
            log,
        )

        # Retry each job using the job manager
        with app.open():
            requeued = 0
            for job_id, queue_name, priority, lock in failed_jobs:
                try:
                    app.job_manager.retry_job_by_id(
                        job_id=job_id,
                        retry_at=utils.utcnow(),
                        priority=priority,
                        queue=queue_name,
                        lock=lock,
                    )
                    requeued += 1
                    log.debug(f"Requeued job {job_id}", job_id=job_id, queue=queue_name)
                except Exception as e:
                    log.error(
                        f"Failed to requeue job {job_id}: {e}",
                        job_id=job_id,
                        error=str(e),
                    )

        if not requeued:
            log.info("No failed jobs found matching the filters")


@cli.command()
def requeue_stalled(
    dataset: str = OPT_DATASET,
    queue: str = OPT_QUEUE,
    task: str = OPT_TASK,
):
    """
    Requeue stalled/orphaned jobs matching the given filters.

    This command finds all jobs with status='doing' whose worker no longer exists
    (orphaned jobs) and retries them by setting their status back to 'todo'.

    Orphaned jobs can occur when the foreign key constraint on worker_id is dropped
    (for performance) and workers are pruned before completing their jobs.
    """
    from procrastinate import utils

    with ErrorHandler(log):
        if settings.in_memory_db:
            log.error("Cannot requeue jobs with in-memory database")
            raise typer.Exit(1)

        db = get_db()
        app = make_app(sync=True)

        # Get orphaned jobs logging iterator
        orphaned_jobs = logged_items(
            db.get_orphaned_jobs(
                dataset=dataset,
                queue=queue,
                task=task,
            ),
            "Requeuing stalled",
            1000,
            "Job",
            log,
        )

        # Retry each job using the job manager
        with app.open():
            requeued = 0
            for job_id, queue_name, priority, lock in orphaned_jobs:
                try:
                    app.job_manager.retry_job_by_id(
                        job_id=job_id,
                        retry_at=utils.utcnow(),
                        priority=priority,
                        queue=queue_name,
                        lock=lock,
                    )
                    requeued += 1
                    log.debug(
                        f"Requeued stalled job {job_id}",
                        job_id=job_id,
                        queue=queue_name,
                    )
                except Exception as e:
                    log.error(
                        f"Failed to requeue stalled job {job_id}: {e}",
                        job_id=job_id,
                        error=str(e),
                    )

        if not requeued:
            log.info("No stalled/orphaned jobs found matching the filters")
