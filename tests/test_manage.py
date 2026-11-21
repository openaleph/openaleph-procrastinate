import re

from procrastinate.schema import SchemaManager

from openaleph_procrastinate.manage import sql


def test_builtin_indexes_match_procrastinate_schema():
    # `ensure_indexes()` drops every index not in DESIRED_INDEXES, so a renamed
    # or new procrastinate index must be listed in BUILTIN_INDEXES
    schema = SchemaManager.get_schema()
    indexes = set(
        re.findall(r"CREATE (?:UNIQUE )?INDEX (\w+) ON procrastinate_jobs\b", schema)
    )
    # unused, dropped on purpose (see procrastinate-performance-optimization.md)
    indexes.discard("idx_procrastinate_jobs_worker_not_null")
    assert indexes | {"procrastinate_jobs_pkey"} == sql.BUILTIN_INDEXES
