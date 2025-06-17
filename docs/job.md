# The Job model

`openaleph_procrastinate.model` provides two models for defining a Job payload. The models are powered by [pydantic](https://docs.pydantic.dev/latest/).

This allows services to import these models and make sure the payloads are valid.

Jobs have some helper methods attached, including `.defer()` for queuing, these should the preferred usage instead of the methods in the `helpers` module.

**Tasks** always receive the instantiated `Job` object as their argument:

See further below for deferring a `Job` to a next processing stage.

```python
from openaleph_procrastinate.model import AnyJob  # a type alias for Job | DatasetJob

@task(app=app)
def my_task(job: AnyJob) -> AnyJob | None:
    # process things
    # if defer to a next stage, return an updated job:
    return next_job
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

There exists a `@classmethod` to create a job for an Entity:

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

To receive the entities from the `followthemoney-store` (to have the most recent version, it might be patched in between by other tasks):

```python
@task(app=app)
def process_entities(job: DatasetJob):
    for entity in job.load_entities():
        do_something(entity)
```

#### Write entities

Write entities or fragments to the store. This writes to the same dataset the original entity(ies) are from.

!!! danger

    This is currently not working for writing entities to **OpenAleph**. Its _FollowTheMoney store_ uses `ftm_collection_<id>` as the table scheme instead of the `dataset` property as an identifier. To put entities into OpenAleph, defer a next stage job with `aleph.procrastinate.put_entities` as the task.

```python
@task(app=app)
def process_entities(job: DatasetJob):
    with job.get_writer() as bulk:
        for entity in job.load_entities():
            fragment = extract_something(entity)
            bulk.add(fragment)
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

To defer (queue) a job to a next stage after processing, return an updated `Job` in the task function:

```python
@task(app=app)
def my_task(job: DatasetJob) -> DatasetJob:
    entities = []
    for entity in job.load_entities():
        result = do_something(entity)
        entities.append(entity)

    # return a new job to defer
    return DatasetJob.from_entities(
        dataset=job.dataset,
        queue=job.queue,  # use the same queue or another one
        task="another_module.tasks.process",  # reference a task
        entities=entities
    )
```


[See the full reference](./reference/model.md)
