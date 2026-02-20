# How to create a service

This section assumes you are familiar with the [architecture](./architecture.md) and [conventions](./conventions.md).

This example is based on [ftm-geocode](https://docs.investigraph.dev/lib/ftm-geocode).

## Prerequisites

Add the latest [`openaleph-procrastinate`](https://github.com/openaleph/openaleph-procrastinate) as a dependency to your project.

pip:

    pip install openaleph-procrastinate

poetry:

    poetry add openaleph-procrastinate


### Configure database connection

Your service needs to access the `procrastinate` task queues in the postgresql database.

- Use the environment variable `OPENALEPH_PROCRASTINATE_DB_URI` which falls back to `OPENALEPH_DB_URI` (default: `postgresql:///openaleph`).
- If your tasks write entities to the [followthemoney-store](https://github.com/alephdata/followthemoney-store), its store needs to be configured if it differs from the main database: `OPENALEPH_FTM_STORE_URI` which falls back to `FTM_STORE_URI`. If it's not set, the main database uri will be used.
- If your tasks need access to the [servicelayer](https://github.com/dataresearchcenter/servicelayer) Archive, configure it properly via the `ARCHIVE_*` env vars.

## Creating a task

Within your application, create a python file `tasks.py` within the project root. This is [by convention](./conventions.md) to have a standardized way of referring to tasks from another program via a string like `<library_name>.tasks.<task_name>`.

### tasks.py

- Import the `openaleph_procrastinate` dependencies
- Create the app that is able to import the tasks
- Register actual tasks that handle [`Jobs`](./job.md)

This file within `ftm-geocode` allows other workers to defer tasks via the identifier `ftm_geocode.tasks.geocode`.

```python
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.tasks import task

from ftm_geocode.geocode import geocode_proxy
from ftm_geocode.settings import Settings

settings = Settings()
app = make_app(__loader__.name)

@task(app=app)
def geocode(job: DatasetJob):
    with job.get_writer() as bulk:
        for proxy in geocode_proxy(settings.geocoders, job.get_entities()):
            bulk.put(proxy)
```

## Run the workers for this service

Use the built-in [procrastinate cli](https://procrastinate.readthedocs.io/en/stable/howto/basics/command_line.html). The app needs to be configured for the environment of this service.

```bash
export PROCRASTINATE_APP=ftm_geocode.tasks.app
```

This worker would subscribe to the `ftm-geocode` queue:

```bash
procrastinate worker -q ftm-geocode
```

## Defer tasks from another service

Another service that has access to the postgresql database can defer tasks to geocode.

Either use a globally [known defer](./reference/defer.md) or follow the manual steps below.

See the [`Job` model](./job.md) and make sure to properly [use the context manager to connect to procrastinate](https://procrastinate.readthedocs.io/en/stable/howto/basics/open_connection.html).

```python
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import DatasetJob

app = make_app()

def defer_job(entity):
    with app.open() as app:
        job = DatasetJob.from_entity(
            dataset="my_dataset",
            queue="ftm-geocode",
            task="ftm_geocode.tasks.geocode",
            entity=entity
        )
        job.defer(app=app)
```

## Defer tasks using the cli

`openaleph_procrastinate` has a command line interface to defer tasks to any queues and services (that usually live somewhere else). This can be used for local debugging / development but as well could serve as an interface for production deployments.

To defer the _Address_ entities of the dataset [de_lobbyregister](https://dataresearchcenter.org/library/de_lobbyregister/) to the geocoding (using [`ftmq`](https://docs.investigraph.dev/lib/ftmq/) for remote loading and filtering):

```bash
ftmq -i https://data.ftm.store/de_lobbyregister/entities.ftm.json -s Address | openaleph-procrastinate defer-entities -q ftm-geocode -t ftm_geocode.tasks.geocode -d de_lobbyregister
```
