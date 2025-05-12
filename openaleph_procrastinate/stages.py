"""
Known stages within the OpenAleph stack
"""

from openaleph_procrastinate.model import Stage

OPENALEPH_PUT_ENTITIES = Stage(
    queue="openaleph", task="aleph.procrastinate.put_entities"
)
