"""sql queries for status aggregation and cancel jobs"""

# HELPER VARS #
JOBS = "procrastinate_jobs"
EVENTS = "procrastinate_events"

SYSTEM_DATASET = "__system__"
DEFAULT_BATCH = "default"

COLUMNS = "dataset, batch, queue_name, task_name, status"

# FILTERS #
F_DATASET = "(%(dataset)s::varchar IS NULL OR dataset = %(dataset)s)"
F_BATCH = "(%(batch)s::varchar IS NULL OR batch = %(batch)s)"
F_QUEUE = "(%(queue)s::varchar IS NULL OR queue_name = %(queue)s)"
F_TASK = "(%(task)s::varchar IS NULL OR task_name = %(task)s)"
F_STATUS = "(%(status)s::procrastinate_job_status IS NULL OR status = %(status)s)"
F_ALL_ANDS = " AND ".join((F_DATASET, F_BATCH, F_QUEUE, F_TASK, F_STATUS))

# FOR INITIAL SETUP #
GENERATED_FIELDS = f"""
ALTER TABLE {JOBS}
ADD COLUMN IF NOT EXISTS dataset TEXT GENERATED ALWAYS AS (
    COALESCE(args->>'dataset', '{SYSTEM_DATASET}')
) STORED;

ALTER TABLE {JOBS}
ADD COLUMN IF NOT EXISTS batch TEXT GENERATED ALWAYS AS (
    COALESCE(args->>'batch', '{DEFAULT_BATCH}')
) STORED;

ALTER TABLE {JOBS}
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

ALTER TABLE {JOBS}
ALTER COLUMN created_at SET DEFAULT NOW();

ALTER TABLE {JOBS}
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

ALTER TABLE {JOBS}
ALTER COLUMN updated_at SET DEFAULT NOW();

CREATE OR REPLACE FUNCTION update_{JOBS}_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_{JOBS}_updated_at ON {JOBS};

CREATE TRIGGER trigger_update_{JOBS}_updated_at
    BEFORE UPDATE ON {JOBS}
    FOR EACH ROW
    EXECUTE FUNCTION update_{JOBS}_updated_at();
"""

# REMOVE FOREIGN KEY CONSTRAINT #
# Foreign key from jobs to workers causes AccessExclusiveLock contention
# during worker cleanup (DELETE triggers CASCADE UPDATE on millions of rows)
# Using loose coupling instead - orphaned worker_id references are acceptable
REMOVE_FOREIGN_KEY = f"""
ALTER TABLE {JOBS} DROP CONSTRAINT IF EXISTS procrastinate_jobs_worker_id_fkey;
"""

# CUSTOM PRUNE STALLED WORKERS FUNCTION #
# Replaces procrastinate's built-in procrastinate_prune_stalled_workers_v1
# The original function just deletes workers, but with FK constraint dropped,
# this leaves jobs in "doing" status with worker_id pointing to deleted workers.
# These orphaned jobs become invisible to stalled job detection.
# This custom version sets worker_id = NULL before deleting, mimicking FK cascade.
CUSTOM_PRUNE_STALLED_WORKERS = f"""
CREATE OR REPLACE FUNCTION procrastinate_prune_stalled_workers_v1(seconds_since_heartbeat float)
RETURNS void AS $$
BEGIN
    -- First, set worker_id to NULL for jobs referencing stalled workers
    -- This mimics the ON DELETE SET NULL behavior of the dropped FK constraint
    -- and allows these jobs to be detected as stalled
    UPDATE {JOBS}
    SET worker_id = NULL
    WHERE status = 'doing'
      AND worker_id IN (
        SELECT id FROM procrastinate_workers
        WHERE last_heartbeat < NOW() - (seconds_since_heartbeat || ' SECOND')::INTERVAL
    );

    -- Then delete the stalled workers (original behavior)
    DELETE FROM procrastinate_workers
    WHERE last_heartbeat < NOW() - (seconds_since_heartbeat || ' SECOND')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
"""

# INDEX TO IMPROVE GENERAL PERFORMANCE AND STATUS QUERIES #
# Based on performance analysis: minimize indices on high-UPDATE tables
INDEXES = f"""

-- Core indices for management and status queries

CREATE INDEX IF NOT EXISTS idx_{JOBS}_dataset
ON {JOBS} (dataset);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_grouping
ON {JOBS} (dataset, batch, queue_name, task_name, status);

-- Fast path index for lock-free jobs (generic, works across all queues)
-- Partial index WHERE clause filters status='todo' AND lock IS NULL
-- Index columns: queue_name for filtering, priority/id for ordering
-- Note: scheduled_at excluded as it's NULL for most jobs (handled in WHERE clause)

CREATE INDEX IF NOT EXISTS idx_{JOBS}_no_lock_fast_path
ON {JOBS}(queue_name, priority DESC, id ASC)
WHERE status = 'todo' AND lock IS NULL;
"""

# OPTIMIZED JOB FETCH FUNCTION #
# Fast path / slow path optimization for ~300x speedup on lock-free jobs
# Most jobs have lock IS NULL, so check them first with simple index lookup
# Only fall back to complex NOT EXISTS logic for jobs with locks
# See: procrastinate-performance-optimization.md (Solution: Fast Path / Slow Path Optimization)
OPTIMIZED_FETCH_FUNCTION = f"""
CREATE OR REPLACE FUNCTION procrastinate_fetch_job_v2(
    target_queue_names character varying[],
    p_worker_id bigint
)
    RETURNS {JOBS}
    LANGUAGE plpgsql
AS $$
DECLARE
    found_jobs {JOBS};
BEGIN
    -- FAST PATH: lock-free jobs (should hit queue-specific partial index)
    -- ~300x faster than slow path for typical workloads
    WITH candidate AS (
        SELECT jobs.id
        FROM {JOBS} AS jobs
        WHERE jobs.status = 'todo'
          AND jobs.lock IS NULL
          AND (target_queue_names IS NULL OR jobs.queue_name = ANY(target_queue_names))
          AND (jobs.scheduled_at IS NULL OR jobs.scheduled_at <= now())
        ORDER BY jobs.priority DESC, jobs.id ASC
        LIMIT 1
        FOR UPDATE OF jobs SKIP LOCKED
    )
    UPDATE {JOBS}
    SET status = 'doing', worker_id = p_worker_id
    FROM candidate
    WHERE {JOBS}.id = candidate.id
    RETURNING {JOBS}.* INTO found_jobs;

    IF FOUND THEN
        RETURN found_jobs;
    END IF;

    -- SLOW PATH: jobs with locks (requires NOT EXISTS check for lock conflicts)
    -- Only executed if fast path returns nothing
    WITH candidate AS (
        SELECT jobs.id
        FROM {JOBS} AS jobs
        WHERE jobs.status = 'todo'
          AND jobs.lock IS NOT NULL
          AND (target_queue_names IS NULL OR jobs.queue_name = ANY(target_queue_names))
          AND (jobs.scheduled_at IS NULL OR jobs.scheduled_at <= now())
          AND NOT EXISTS (
              SELECT 1
              FROM {JOBS} AS other_jobs
              WHERE other_jobs.lock = jobs.lock
                AND (
                    other_jobs.status = 'doing'
                    OR (
                        other_jobs.status = 'todo'
                        AND (
                            other_jobs.priority > jobs.priority
                            OR (other_jobs.priority = jobs.priority AND other_jobs.id < jobs.id)
                        )
                    )
                )
          )
        ORDER BY jobs.priority DESC, jobs.id ASC
        LIMIT 1
        FOR UPDATE OF jobs SKIP LOCKED
    )
    UPDATE {JOBS}
    SET status = 'doing', worker_id = p_worker_id
    FROM candidate
    WHERE {JOBS}.id = candidate.id
    RETURNING {JOBS}.* INTO found_jobs;

    RETURN found_jobs;
END;
$$;
"""


# QUERY JOB STATUS #
# query status aggregation, optional filtered for dataset.
# this returns result rows with these values in its order:
# dataset,batch,queue_name,task_name,status,jobs count,first created,last updated
STATUS_SUMMARY = f"""
SELECT {COLUMNS},
    COUNT(*) AS jobs,
    MIN(created_at) AS min_ts,
    MAX(updated_at) AS max_ts
FROM {JOBS}
WHERE {F_DATASET}
GROUP BY {COLUMNS}
ORDER BY {COLUMNS}
"""

# only return status aggregation for active datasets
STATUS_SUMMARY_ACTIVE = f"""
SELECT {COLUMNS},
    COUNT(*) AS jobs,
    MIN(created_at) AS min_ts,
    MAX(updated_at) AS max_ts
FROM {JOBS} j1
WHERE {F_DATASET}
AND EXISTS (
    SELECT 1 FROM {JOBS} j2
    WHERE j2.dataset = j1.dataset
    AND j2.status IN ('todo', 'doing')
)
GROUP BY {COLUMNS}
ORDER BY {COLUMNS}
"""


ALL_JOBS = f"""
SELECT id, status, args
FROM {JOBS}
WHERE (updated_at BETWEEN %(min_ts)s AND %(max_ts)s)
AND {F_ALL_ANDS}
"""

# CANCEL OPS #
# they follow the logic from here:
# https://github.com/procrastinate-org/procrastinate/blob/main/procrastinate/sql/schema.sql
# but alter the table in batch instead of running it one by one per job id.
# This is equivalent to the function `procrastinate_cancel_job_v1` with delete=true,abort=true
CANCEL_JOBS = f"""
DELETE FROM {JOBS} WHERE status = 'todo'
AND {F_DATASET} AND {F_BATCH} AND {F_QUEUE} AND {F_TASK};

UPDATE {JOBS} SET abort_requested = true, status = 'cancelled'
WHERE status = 'todo'
AND {F_DATASET} AND {F_BATCH} AND {F_QUEUE} AND {F_TASK};

UPDATE {JOBS} SET abort_requested = true
WHERE status = 'doing'
AND {F_DATASET} AND {F_BATCH} AND {F_QUEUE} AND {F_TASK};
"""

# REQUEUE FAILED JOBS #
# Get failed jobs with necessary fields for retrying
GET_FAILED_JOBS = f"""
SELECT id, queue_name, priority, lock
FROM {JOBS}
WHERE status = 'failed'
AND {F_DATASET} AND {F_BATCH} AND {F_QUEUE} AND {F_TASK}
"""

# DETECT ORPHANED JOBS #
# Find jobs stuck in "doing" status whose workers no longer exist.
# This can happen when the FK constraint is dropped (for performance) and workers
# are pruned before the custom prune function is installed, or if using an older
# version of procrastinate's prune function.
GET_ORPHANED_JOBS = f"""
SELECT id, queue_name, priority, lock
FROM {JOBS}
WHERE status = 'doing'
  AND worker_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM procrastinate_workers w WHERE w.id = {JOBS}.worker_id
  )
  AND {F_DATASET} AND {F_BATCH} AND {F_QUEUE} AND {F_TASK}
"""
