from collections import defaultdict
from typing import Generator

from openaleph_procrastinate.manage.db import get_db
from openaleph_procrastinate.model import (
    SYSTEM_DATASET,
    BatchStatus,
    DatasetStatus,
    QueueStatus,
    TaskStatus,
)

DEFAULT_BACH = "default"


def _gather_status(
    dataset: str | None = None, active_only: bool | None = True
) -> Generator[DatasetStatus, None, None]:
    db = get_db()
    tree = lambda: defaultdict(tree)  # noqa: E731
    data = tree()
    for (
        dataset_name,
        batch,
        queue,
        task,
        status,
        jobs,
        min_ts,
        max_ts,
    ) in db.iterate_status(dataset, active_only=active_only):
        data[dataset_name][batch][queue][task]["counts"][status] = jobs
        data[dataset_name][batch][queue][task]["min_ts"][status] = min_ts
        data[dataset_name][batch][queue][task]["max_ts"][status] = max_ts

    for dataset_name, batches in data.items():
        dataset_status = DatasetStatus(name=dataset_name or SYSTEM_DATASET)
        for batch, queues in batches.items():
            batch_status = BatchStatus(name=batch or DEFAULT_BACH)
            for queue, tasks in queues.items():
                queue_status = QueueStatus(name=queue)
                for task, stats in tasks.items():
                    min_ts = min(stats["min_ts"].values())
                    max_ts = min(stats["max_ts"].values())
                    task_status = TaskStatus(
                        name=task,
                        **stats["counts"],
                        min_ts=min_ts,
                        max_ts=max_ts,
                    )
                    queue_status.add_child_stats(task_status)
                    queue_status.tasks.append(task_status)
                batch_status.add_child_stats(queue_status)
                batch_status.queues.append(queue_status)
            dataset_status.add_child_stats(batch_status)
            dataset_status.batches.append(batch_status)
        yield dataset_status


def get_status(active_only: bool | None = True) -> Generator[DatasetStatus, None, None]:
    yield from _gather_status(active_only=active_only)


def get_dataset_status(dataset: str, active_only: bool | None = True) -> DatasetStatus:
    for status in _gather_status(dataset, active_only):
        return status
    return DatasetStatus(name=dataset)
