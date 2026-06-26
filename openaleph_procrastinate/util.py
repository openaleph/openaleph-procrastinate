from typing import Type

from anystore.logging import get_logger
from followthemoney import E, ValueEntity
from followthemoney.namespace import Namespace
from followthemoney.proxy import EntityProxy
from followthemoney.util import make_entity_id
from ftmq.store.fragments import get_fragments
from ftmq.util import make_entity

from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)

# FTMQ BulkLoader default size = 1000
QUERY_LIMIT = 1000

openaleph_settings = OpenAlephSettings()
sqlalchemy_pool = {
    "pool_size": openaleph_settings.db_pool_size,
    "max_overflow": openaleph_settings.db_pool_size,
}


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
        stub.add("ancestors", e.get("ancestors", quiet=q), quiet=q)
        return stub


def get_page_entity_fragments(
    entity: EntityProxy, ftm_dataset: str, ns: Namespace, origin: str = "ingest"
):
    """
    Get all the Page entities corresponding to a Pages entity
    """
    store = get_fragments(
        ftm_dataset,
        origin=origin,
        database_uri=openaleph_settings.fragments_uri,
        **sqlalchemy_pool,
    )
    current_page = 1
    while True:
        page_batch = range(current_page, current_page + QUERY_LIMIT)
        page_ids = set(
            make_entity_id(entity.id, p, key_prefix=ftm_dataset) for p in page_batch
        )
        # https://github.com/openaleph/ingest-file/issues/30
        page_id_no_ns = set(
            make_entity_id(entity.id.split(".")[0], p, key_prefix=ftm_dataset)
            for p in page_batch
        )
        page_ids.update(page_id_no_ns)
        # apply correct namespace
        page_ids = list(map(ns.sign, page_ids))
        ix = 1
        for ix, fragment in enumerate(  # noqa: B007
            store.fragments(page_ids, "default"), 1
        ):
            yield fragment
        if ix <= QUERY_LIMIT:
            break
        current_page += QUERY_LIMIT
