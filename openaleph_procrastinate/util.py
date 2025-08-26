from anystore.logging import get_logger
from followthemoney.proxy import EntityProxy

log = get_logger(__name__)


def make_stub_entity(e: EntityProxy) -> EntityProxy | None:
    """
    Reduce an entity to its ID and schema
    """
    if not e.id:
        log.warning("Entity has no ID!")
        return
    return EntityProxy.from_dict(
        {"id": e.id, "schema": e.schema.name, "caption": e.caption}
    )


def make_checksum_entity(
    e: EntityProxy, quiet: bool | None = False
) -> EntityProxy | None:
    """
    Reduce an entity to its ID, schema and contentHash property
    """
    q = bool(quiet)
    stub = make_stub_entity(e)
    if stub is not None:
        stub.add("contentHash", e.get("contentHash", quiet=q), quiet=q)
        return stub
