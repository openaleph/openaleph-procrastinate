from openaleph_procrastinate.logging import (
    extract_job_summary,
    patch_procrastinate_logging,
)


def test_extract_job_summary_with_entities():
    entities = [
        {
            "id": "doc-001",
            "schema": "Document",
            "properties": {"contentHash": ["abc123"]},
        },
        {
            "id": "doc-002",
            "schema": "Document",
            "properties": {"contentHash": ["def456"]},
        },
    ]
    task_kwargs = {
        "dataset": "my-dataset",
        "batch": "batch-1",
        "payload": {"entities": entities},
    }
    summary = extract_job_summary(task_kwargs)
    assert summary["dataset"] == "my-dataset"
    assert summary["batch"] == "batch-1"
    assert summary["entities_count"] == 2
    assert summary["entity_id_min"] == "doc-001"
    assert summary["entity_id_max"] == "doc-002"
    assert summary["entity_ids"] == ["doc-001", "doc-002"]
    assert summary["content_hash_min"] == "abc123"
    assert summary["content_hash_max"] == "def456"


def test_extract_job_summary_empty_payload():
    assert extract_job_summary({}) == {}
    assert extract_job_summary({"payload": "not-a-dict"}) == {}
    assert extract_job_summary({"payload": {}}) == {}
    assert extract_job_summary({"payload": {"entities": []}}) == {}


def test_patch_procrastinate_logging():
    """Verify the monkey-patch produces concise call_string and stripped log_context."""
    from procrastinate.jobs import Job as ProcrastinateJob

    patch_procrastinate_logging()

    job = ProcrastinateJob(
        id=42,
        queue="test-queue",
        lock="lock",
        queueing_lock=None,
        task_name="mylib.tasks.process",
        task_kwargs={
            "dataset": "investigation",
            "payload": {
                "entities": [
                    {"id": "ent-1", "properties": {"contentHash": ["aaa"]}},
                    {"id": "ent-2", "properties": {"contentHash": ["bbb"]}},
                ]
            },
        },
        scheduled_at=None,
        attempts=0,
    )

    # call_string should be short, not include the full payload repr
    assert job.call_string == "mylib.tasks.process[42]"

    # log_context should NOT contain task_kwargs but should have summary fields
    ctx = job.log_context()
    assert "task_kwargs" not in ctx
    assert ctx["dataset"] == "investigation"
    assert ctx["entities_count"] == 2
    assert ctx["entity_ids"] == ["ent-1", "ent-2"]
