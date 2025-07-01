# Conventions

To keep the codebase simple and separated, for now the different services and programs doesn't know much about each other. Deferring tasks from one service to another could be described as _"fire and forget"_ as the deferring service doesn't know if the target queue and task actually exists.

This approach allows a more simplified codebase without the need to keep different programs in sync, but might introduce trouble – so this approach is subject to change if we move forward with `openaleph_procrastinate`.

For now, this requires some conventions – they are not enforced and might need some exceptions for more complex programs, but they should be followed if possible.

## Tasks

Live in a `tasks` submodule of the program, so that other services can reference a tasks for deferring with the string identifier `<library_name>.tasks.<task_name>`.

Tasks always take a [`Job`](./job.md) as its only argument. To defer a new job to a new _Stage_ after processing the task, explicitly defer it at the end of the task (or use one of the [known defers](./reference/defer.md) helpers).

[We use our own task decorator to add custom middleware](https://procrastinate.readthedocs.io/en/stable/howto/advanced/middleware.html) defined at `openaleph_procrastinate.tasks`

The function signature for a task therefore looks as follows:

```python
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import Job, Defers
from openaleph_procrastinate.tasks import task

app = make_app(__loader__.name)

@task(app=app)
def my_task(job: Job) -> None:
    # process things
    new_job = Job(...)  # create new job
    # defer it
    new_job.defer(app=app)
```

[Known defers](./reference/defer.md)

## App

The app needs to be instantiated for the current program context. The app object should live in the `tasks` submodule (see above).

## Queues

If a service only needs one queue (a queue can have multiple tasks subscribed to), it should be the name of this service, e.g. `ftm-geocode`.

If a service needs more then one queue, they should be prefixed with it's library name and "sub-queues" should be separated with double dashes: `ftm-analyze--mentions`.

## Worker

Following the conventions for _Tasks_, _App_ and _Queues_, workers should use the built-in `procrastinate` cli if possible and for each program configured and started like this:

```bash
export PROCRASTINATE_APP=<library_name>.tasks.app
procrastinate worker -q <library-name>
```
