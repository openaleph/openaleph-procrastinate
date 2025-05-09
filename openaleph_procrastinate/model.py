from pathlib import Path
from typing import Any, BinaryIO, ContextManager, Generator, Self, TypeAlias

from followthemoney import model
from followthemoney.proxy import EntityProxy
from ftmstore.loader import BulkLoader
from procrastinate.app import App
from pydantic import BaseModel, Field

from openaleph_procrastinate import helpers


class Stage(BaseModel):
    """Define an arbitrary next stage for a job"""

    # model: str
    queue: str
    task: str

    def make_job(self: Self, job: "AnyJob") -> "AnyJob":
        job.queue = self.queue
        job.task = self.task
        return job


class Job(Stage):
    """
    A job with arbitrary payload
    """

    payload: dict[str, Any]
    stages: list[Stage] = Field(default=[])

    def defer(self: Self, app: App) -> None:
        data = self.model_dump(mode="json")
        app.configure_task(name=self.task, queue=self.queue).defer(**data)


class DatasetJob(Job):
    """
    A job with arbitrary payload bound to a `dataset`.

    Depending on the payload, there are helpers for accessing archive files or
    loading entities.
    """

    dataset: str

    # Helpers for file jobs that access the servicelayer archive

    @property
    def content_hash(self) -> str:
        """Get the content hash from the payload, if any"""
        assert "content_hash" in self.payload, "No `content_hash` in task payload"
        return self.payload["content_hash"]

    @classmethod
    def from_content_hash(
        cls, dataset: str, queue: str, task: str, content_hash: str
    ) -> Self:
        """Make a job to process a file for a dataset"""
        payload = {"content_hash": content_hash}
        return cls(dataset=dataset, queue=queue, task=task, payload=payload)

    def open(self: Self) -> ContextManager[BinaryIO]:
        """Open the file attached to this job"""
        return helpers.open_file(self.content_hash)

    def get_localpath(self: Self) -> ContextManager[Path]:
        """Get a temporary path for the file attached to this job"""
        return helpers.get_localpath(self.content_hash)

    # Helpers for entity jobs that access the ftm store

    @property
    def entity(self) -> EntityProxy:
        """Make a proxy from the payload"""
        return model.get_proxy(self.payload)

    def load_entity(self: Self) -> EntityProxy:
        """Load the entity from the store to refresh it to the latest data"""
        assert self.entity.id is not None, "No id for entity"
        return helpers.load_entity(self.dataset, self.entity.id)

    def get_writer(self: Self) -> ContextManager[BulkLoader]:
        """Get the writer for the dataset of the current entity"""
        return helpers.entity_writer(self.dataset)

    @classmethod
    def from_entity(
        cls, dataset: str, queue: str, task: str, entity: EntityProxy
    ) -> Self:
        """Make a job to process an entity for a dataset"""
        return cls(dataset=dataset, queue=queue, task=task, payload=entity.to_dict())

    # Multiple entities are stored in `entities` key of payload`

    def get_entities(self) -> Generator[EntityProxy, None, None]:
        """
        Get the entities from the payload
        """
        assert "entities" in self.payload, "No entities in payload"
        for data in self.payload["entities"]:
            yield model.get_proxy(data)

    def load_entities(self: Self) -> Generator[EntityProxy, None, None]:
        """Load the entities from the store to refresh it to the latest data"""
        assert "entities" in self.payload, "No entities in payload"
        for data in self.payload["entities"]:
            yield helpers.load_entity(self.dataset, data["id"])


AnyJob: TypeAlias = Job | DatasetJob
