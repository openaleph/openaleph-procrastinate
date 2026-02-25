from typing import Type

from anystore.logging import get_logger
from followthemoney import E, ValueEntity
from ftmq.util import make_entity

log = get_logger(__name__)


def make_stub_entity(e: E, entity_type: Type[E] | None = ValueEntity) -> E:
    """
    Reduce an entity to its ID and schema
    """
    if not e.id:
        raise RuntimeError("Entity has no ID!")
    return make_entity(
        {"id": e.id, "schema": e.schema.name, "caption": e.caption}, entity_type
    )


def make_file_entity(
    e: E, entity_type: Type[E] | None = ValueEntity, quiet: bool | None = False
) -> E | None:
    """
    Reduce an entity to its ID, schema and contentHash property
    """
    q = bool(quiet)
    stub = make_stub_entity(e, entity_type)
    if stub is not None:
        stub.add("contentHash", e.get("contentHash", quiet=q), quiet=q)
        stub.add("fileName", e.get("fileName", quiet=q), quiet=q)
        stub.add("parent", e.get("parent", quiet=q), quiet=q)
        return stub
