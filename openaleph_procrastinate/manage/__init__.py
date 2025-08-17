from openaleph_procrastinate.manage.db import get_db


def cancel_jobs(
    dataset: str | None = None,
    batch: str | None = None,
    queue: str | None = None,
    task: str | None = None,
) -> None:
    db = get_db()
    db.cancel_jobs(dataset, batch, queue, task)
