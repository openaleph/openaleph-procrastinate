from typing import Annotated, Optional

import typer
from anystore.cli import ErrorHandler
from anystore.io import smart_stream_json
from anystore.logging import configure_logging, get_logger
from ftmq.io import smart_read_proxies
from rich import print

from openaleph_procrastinate import __version__, model, tasks
from openaleph_procrastinate.app import init_db as _init_db
from openaleph_procrastinate.app import make_app
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
    _init_db()
