from typing import Annotated, Optional

import typer
from anystore.cli import ErrorHandler
from anystore.io import smart_stream_json
from anystore.logging import configure_logging
from ftmq.io import smart_stream_proxies
from rich import print

from openaleph_procrastinate import __version__, model, tasks
from openaleph_procrastinate.app import app
from openaleph_procrastinate.settings import OpenAlephSettings

settings = OpenAlephSettings()

cli = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=settings.debug)

DEFAULT_QUEUE = "default"
DEFAULT_TASK = "openaleph_procrastinate.tasks.dummy_task"

OPT_INPUT_URI = typer.Option("-", "-i", help="Input uri, default stdin")
OPT_DATASET = typer.Option(..., "-d", help="Dataset")
OPT_QUEUE = typer.Option(DEFAULT_QUEUE, "-q", help="Queue name")
OPT_TASK = typer.Option(
    "openaleph_procrastinate.tasks.dummy_task", "-t", help="Task module path"
)


@cli.callback(invoke_without_command=True)
def cli_opal_procrastinate(
    version: Annotated[Optional[bool], typer.Option(..., help="Show version")] = False,
):
    if version:
        print(__version__)
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
    with ErrorHandler(), app.open():
        for proxy in smart_stream_proxies(input_uri):
            job = model.DatasetJob.from_entity(
                dataset=dataset, queue=queue, task=task, entity=proxy
            )
            job.defer(app)


@cli.command()
def defer_jobs(input_uri: str = OPT_INPUT_URI):
    """
    Defer jobs from an input json stream
    """
    with ErrorHandler(), app.open():
        for data in smart_stream_json(input_uri):
            job = tasks.unpack_job(data)
            job.defer(app)
