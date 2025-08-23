"""sql queries for status aggregation and cancel jobs"""

# HELPER VARS #
JOBS = "procrastinate_jobs"
EVENTS = "procrastinate_events"
CTE_JOB_STATUS = "cte_job_status"  # CTE

SYSTEM_DATASET = "__system__"
DEFAULT_BATCH = "default"

COLUMNS = "dataset, batch, queue_name, task_name, status"
MAX_ID = "MAX(id) AS max_id"
MIN_ID = "MIN(id) AS min_id"

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
"""

# INDEXES FOR STATUS QUERY #
INDEXES = f"""
CREATE INDEX IF NOT EXISTS idx_{JOBS}_args
ON {JOBS} USING GIN (args);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_dataset
ON {JOBS} (dataset);

CREATE INDEX IF NOT EXISTS idx_{JOBS}_batch
ON {JOBS} (batch);

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
# query status aggregation, optional filtered for dataset. this is quite
# expensive, make sure the additional indexes and generated fields exist.
# this returns result rows with these values in its order:
# dataset,batch,queue_name,task_name,status,jobs count,first event,last event
STATUS_SUMMARY = f"""
WITH {CTE_JOB_STATUS} AS (
    SELECT {COLUMNS}, COUNT(*) AS jobs, {MIN_ID}, {MAX_ID} FROM {JOBS}
    WHERE {F_DATASET}
    GROUP BY {COLUMNS} ORDER BY {COLUMNS}
)
SELECT {COLUMNS},
MAX(jobs), MIN(e1.at), MAX(e2.at) FROM {CTE_JOB_STATUS}
LEFT JOIN {EVENTS} e1 ON min_id = e1.job_id
LEFT JOIN {EVENTS} e2 ON max_id = e2.job_id
GROUP BY {COLUMNS} ORDER BY {COLUMNS}
"""

# only return status aggregation for active datasets
STATUS_SUMMARY_ACTIVE = f"""
WITH {CTE_JOB_STATUS} AS (
    SELECT {COLUMNS}, COUNT(*) AS jobs, {MIN_ID}, {MAX_ID} FROM {JOBS} j1
    WHERE {F_DATASET}
    AND EXISTS (
        SELECT 1 FROM {JOBS} j2
        WHERE j2.dataset = j1.dataset
        AND j2.status IN ('todo', 'doing')
    )
    GROUP BY {COLUMNS} ORDER BY {COLUMNS}
)
SELECT {COLUMNS},
MAX(jobs), MIN(e1.at), MAX(e2.at) FROM {CTE_JOB_STATUS}
LEFT JOIN {EVENTS} e1 ON min_id = e1.job_id
LEFT JOIN {EVENTS} e2 ON max_id = e2.job_id
GROUP BY {COLUMNS} ORDER BY {COLUMNS}
"""


ALL_JOBS = f"""
SELECT id, status, args FROM {JOBS} WHERE id IN (
SELECT job_id FROM {EVENTS}
WHERE (at BETWEEN %(min_ts)s AND %(max_ts)s)
AND {F_ALL_ANDS}
)
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
