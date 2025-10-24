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
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE {JOBS}
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

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

# INDEXES FOR STATUS QUERY #
INDEXES = f"""
CREATE INDEX IF NOT EXISTS idx_{JOBS}_args
ON {JOBS} USING GIN (args);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_dataset
ON {JOBS} (dataset);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_batch
ON {JOBS} (batch);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_created_at
ON {JOBS} (created_at);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_updated_at
ON {JOBS} (updated_at);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_task
ON {JOBS} (task_name);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_status
ON {JOBS} (status);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_grouping
ON {JOBS} (dataset, batch, queue_name, task_name, status);

CREATE INDEX IF NOT EXISTS idx_{EVENTS}_job_id_at
ON {EVENTS} (job_id, at);
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
