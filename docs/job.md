# The Job model

`openaleph_procrastinate.model` provides two models for defining a Job payload. The models are powered by [pydantic](https://docs.pydantic.dev/latest/).

This allows services to import these models and make sure the payloads are valid.

Jobs have some helper methods attached, including `.defer()` for queuing, these should the preferred usage instead of the methods in the `helpers` module.

**Tasks** always receive the instantiated `Job` object as their argument:

```python
from openaleph_procrastinate.model import AnyJob  # a type alias for Job | DatasetJob

@task(app=app)
def my_task(job: AnyJob) -> AnyJob:
    # process things
    return job
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

A concrete Job bound to a dataset via its property `dataset`. This will be the most common used Job model for ingesting files, analyzing and indexing entities.

They have some helper methods to access file objects or entities:

### A job for processing a file from the servicelayer

```python
job = DatasetJob(
    dataset="my_dataset",
    queue="ingest",
    task="ingestors.tasks.ingest",
    payload={"content_hash": "<sha1>"}
)
```

There exists a `@classmethod` to create the same object:

```python
job = DatasetJob.from_conten_hash(
    dataset="my_dataset",
    queue="ingest",
    task="ingestors.task.ingest",
    content_hash="<sha1>"
)
```

#### Get a file-handler within a task

Get a `BinaryIO` context manager that behaves the same like file-like `.open()`

```python
@task(app=app)
def process_file(job: DatasetJob):
    with job.open_file() as fh:
        some_function(fh)
```

Under the hood, the file is retrieved from the servicelayer Archive and stored in a local temporary folder. After leaving the context, the file is cleaned up (deleted) locally.

#### Get a temporary file path within a task

Some procedures require a path instead of a file handler. The returned path is a `pathlib.Path` object:

```python
@task(app=app)
def process_file(job: DatasetJob):
    with job.get_localpath() as path:
        subprocess.run(f"some-program -f {path}")
```

Under the hood, the file is retrieved from the servicelayer Archive and stored in a local temporary folder. After leaving the context, the file is cleaned up (deleted) locally.

### A job for processing one or more entities

**TODO** discuss & decide if Jobs should separate payloads for 1 and >1 entities or always have an iterable of entities in the payload (which could have the length of 1).

```python
job = DatasetJob(
    dataset="my_dataset",
    queue="index",
    task="aleph.tasks.index_proxy",
    payload={"id": "1", "schema": "Person", "properties": {"name": ["Jane Doe"]}}
)
```

There exists a `@classmethod` to create the same object:

```python
job = DatasetJob.from_entity(
    dataset="my_dataset",
    queue="index",
    task="aleph.tasks.index_proxy",
    entity=entity  # instance of `followthemoney.model.EntityProxy`
)
```

Multiple entities (for batch processing):

```python
job = DatasetJob(
    dataset="my_dataset",
    queue="index",
    task="aleph.tasks.index_proxy",
    payload={"entities": [...]}
)
```

#### Get the entity or entities

This property parses the payload into an `EntityProxy` object:

```python
@task(app=app)
def process_entity(job: DatasetJob):
    entity = job.entity
```

To receive the entity from the `followthemoney-store` (to have the most recent version, it might be patched in between by other tasks):

```python
@task(app=app)
def process_entity(job: DatasetJob):
    entity = job.load_entity()
```

Get multiple entities from the payload:

```python
@task(app=app)
def process_entities(job: DatasetJob):
    for entity in job.get_entities():
        do_something(entity)
```

To receive the entities from the `followthemoney-store` (to have the most recent version, it might be patched in between by other tasks):

```python
@task(app=app)
def process_entities(job: DatasetJob):
    for entity in job.load_entities():
        do_something(entity)
```

Write entities or fragments to the store. This writes to the same dataset the original entity(ies) are from.

```python
@task(app=app)
def process_entities(job: DatasetJob):
    with job.get_writer() as bulk:
        for entity in job.load_entities():
            fragment = extract_something(entity)
            bulk.add(fragment)
```

The bulk writer is flushed when leaving the context.


[See the full reference](./reference/model.md)
