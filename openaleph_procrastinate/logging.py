from __future__ import annotations

from banal import ensure_dict


def extract_job_summary(task_kwargs: dict) -> dict:
    """Extract useful structured fields from job task_kwargs."""
    summary: dict = {}
    dataset = task_kwargs.get("dataset")
    if dataset:
        summary["dataset"] = dataset
    batch = task_kwargs.get("batch")
    if batch:
        summary["batch"] = batch
    payload = task_kwargs.get("payload")
    if not isinstance(payload, dict):
        return summary
    entities = payload.get("entities")
    if not isinstance(entities, list) or not entities:
        return summary
    summary["entities_count"] = len(entities)
    entity_ids = [e["id"] for e in entities if isinstance(e, dict) and e.get("id")]
    if entity_ids:
        summary["entity_id_min"] = min(entity_ids)
        summary["entity_id_max"] = max(entity_ids)
        if len(entity_ids) < 11:
            summary["entity_ids"] = entity_ids
    content_hashes = [
        h
        for e in entities
        if isinstance(e, dict)
        for h in ensure_dict(e.get("properties")).get("contentHash", [])
    ]
    if content_hashes:
        summary["content_hash_min"] = min(content_hashes)
        summary["content_hash_max"] = max(content_hashes)
    return summary


def patch_procrastinate_logging():
    """Patch procrastinate to produce concise, structured job logs.

    Upstream procrastinate logs full repr() of all task kwargs in
    Job.call_string, creating extremely noisy log lines when payloads
    contain entity data. This patch:
    1. Shortens call_string to just task_name[id]
    2. Strips the full payload from log_context()
    3. Promotes dataset/entity/hash summary to top-level structlog kwargs
    """
    from procrastinate.jobs import Job
    from procrastinate.worker import Worker

    @property
    def call_string(self):
        return f"{self.task_name}[{self.id}]"

    Job.call_string = call_string

    _original_log_context = Job.log_context

    def log_context(self):
        ctx = _original_log_context(self)
        ctx.pop("task_kwargs", None)
        ctx.update(extract_job_summary(self.task_kwargs))
        return ctx

    Job.log_context = log_context

    _original_log_extra = Worker._log_extra

    def _log_extra(self, action, context, job_result, **kwargs):
        extra = _original_log_extra(
            self, action=action, context=context, job_result=job_result, **kwargs
        )
        if context:
            extra["task_name"] = context.job.task_name
            extra["queue_name"] = context.job.queue
            extra.update(extract_job_summary(context.job.task_kwargs))
        return extra

    Worker._log_extra = _log_extra
