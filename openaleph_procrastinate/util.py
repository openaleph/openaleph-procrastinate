from typing import Type

from anystore.logging import get_logger
from followthemoney import E, ValueEntity
from followthemoney.namespace import Namespace
from followthemoney.proxy import EntityProxy
from followthemoney.util import make_entity_id
from ftmq.types import EntityProxies
from ftmq.util import make_entity

from openaleph_procrastinate.repository import get_entity_store

log = get_logger(__name__)

# FTMQ BulkLoader default size = 1000
QUERY_LIMIT = 1000


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
        stub.add("mimeType", e.get("mimeType", quiet=q), quiet=q)
        stub.add("parent", e.get("parent", quiet=q), quiet=q)
        stub.add("ancestors", e.get("ancestors", quiet=q), quiet=q)
        return stub


def get_page_entity_fragments(
    entity: EntityProxy, ftm_dataset: str, ns: Namespace, origin: str = "ingest"
) -> EntityProxies:
    """
    Get all the Page entities corresponding to a Pages entity.

    Page ids are derived rather than looked up, so they are queried in batches
    of `QUERY_LIMIT` until a batch comes back incomplete. Both the signed and
    the unsigned form of each id is asked for: the legacy store namespaces
    entities, the lakehouse never does.
    """
    if not entity.id:
        raise RuntimeError("Entity has no ID!")
    # https://github.com/openaleph/ingest-file/issues/30
    keys = (entity.id, entity.id.split(".")[0])
    store = get_entity_store(ftm_dataset, origin)
    current_page = 1
    while True:
        page_batch = range(current_page, current_page + QUERY_LIMIT)
        page_ids = {
            id_
            for key in keys
            for p in page_batch
            if (id_ := make_entity_id(key, p, key_prefix=ftm_dataset))
        }
        page_ids.update(signed for i in set(page_ids) if (signed := ns.sign(i)))
        found = 0
        for page in store.iterate(page_ids):
            found += 1
            yield page
        # pages are numbered consecutively, so an incomplete batch is the last
        if found < QUERY_LIMIT:
            break
        current_page += QUERY_LIMIT
