# The Job model

`openaleph_procrastinate.model` provides two models for defining a Job payload. The models are powered by [pydantic](https://docs.pydantic.dev/latest/).

This allows services to import these models and make sure the payloads are valid.

Jobs have some helper methods attached, including `.defer()` for queuing, these should the preferred usage instead of the methods in the `helpers` module.

**Tasks** always receive the instantiated `Job` object as their argument:

See further below for deferring a `Job` to a next processing stage.

```python
from openaleph_procrastinate.model import AnyJob, Defers

@task(app=app)
def my_task(job: AnyJob) -> Defers:
    # process things
    # if defer to a next stage, return an updated job:
    yield next_job
    # or return None (implicit)
```

## Job data payload

All jobs need the required data:

```python
job = Job(
    queue="<queue-name>",
    task="<service>.tasks.<task_name>",
    payload={}  # actual job payload
)
```

A `DatasetJob` (see below) has the additional property `dataset`.

## Arbitrary Job

`openaleph_procrastinate.model.Job`

A generic Job not bound to a dataset. They can be used for management purposes and other tasks not related to a specific dataset (Aleph wording: _"Collection"_).

## Dataset Job

`openaleph_procrastinate.model.DatasetJob`

A concrete Job bound to a dataset via its property `dataset` (Aleph wording: _"Collection"_). This will be the most common used Job model for ingesting files, analyzing and indexing entities.

Entities in the job payload are always an array in `entities` key even if it is a job only for 1 Entity.

They have some helper methods to access file objects or entities:

### A job for processing one or more entities

```python
job = DatasetJob(
    dataset="my_dataset",
    queue="index",
    task="aleph.tasks.index_proxy",
    payload={"entities": [...], "context": {ctx}}
)
```

There exists a `@classmethod` to create a job for an iterable of _Entities_:

```python
job = DatasetJob.from_entities(
    dataset="my_dataset",
    queue="index",
    task="aleph.tasks.index_proxy",
    entities=[...]  # instances of `followthemoney.model.EntityProxy`
)
```

#### Get entities

Get the entities from the payload:

```python
@task(app=app)
def process_entities(job: DatasetJob):
    for entity in job.get_entities():
        do_something(entity)
```

To receive the entities from the `followthemoney-store` (to have the most recent version, because it might be patched in between by other tasks):

```python
@task(app=app)
def process_entities(job: DatasetJob):
    for entity in job.load_entities():
        do_something(entity)
```

#### Write entities

Write entities or fragments to the store. This writes to the same dataset the original entity(ies) are from.

```python
@task(app=app)
def process_entities(job: DatasetJob):
    with job.get_writer() as bulk:
        for entity in job.load_entities():
            fragment = extract_something(entity)
            bulk.put(fragment)
```

The bulk writer is flushed when leaving the context.


### A job for processing file entities from the servicelayer

The entities must have [`contentHash`](https://followthemoney.tech/explorer/schemata/Document/#property-contentHash) properties.

```python
job = DatasetJob(
    dataset="my_dataset",
    queue="ingest",
    task="ingestors.tasks.ingest",
    payload={"entities": [...]}
)
```

#### Get file-handlers within a task

Get a `BinaryIO` context manager that behaves the same like file-like `.open()` for each entity and its `contentHash` properties:

```python
@task(app=app)
def process_file(job: DatasetJob):
    for reference in job.get_file_references():
        with reference.open() as fh:
            some_function(fh, entity=reference.entity)
```

Under the hood, the file is retrieved from the [servicelayer](https://github.com/openaleph/servicelayer) Archive and stored in a local temporary folder. After leaving the context, the file is cleaned up (deleted) locally.

#### Get temporary file paths within a task

Some procedures require a path instead of a file handler. The returned path is a `pathlib.Path` object:

```python
@task(app=app)
def process_file(job: DatasetJob):
    for reference in job.get_file_references():
        with handler.get_localpath() as path:
            subprocess.run(f"some-program -f {path}")
```

Under the hood, the file is retrieved from the [servicelayer](https://github.com/openaleph/servicelayer) Archive and stored in a local temporary folder. After leaving the context, the file is cleaned up (deleted) locally.


## Defer to next stage

To defer (queue) a job to a next stage after processing, explicitly call the defer method either on the updated or newly created `Job` object itself or use one of the [known defers](./reference/defer.md).

```python
@task(app=app)
def my_task(job: DatasetJob) -> None:
    entities = []
    for entity in job.load_entities():
        result = do_something(entity)
        entities.append(entity)

    # yield a new job to defer
    next_job = DatasetJob.from_entities(
        dataset=job.dataset,
        queue=job.queue,  # use the same queue or another one
        task="another_module.tasks.process",  # reference a task
        entities=entities
    )
    next_job.defer(app=app)
```


[See the full reference](./reference/model.md)
