from followthemoney.proxy import EntityProxy


def make_stub_entity(e: EntityProxy) -> EntityProxy:
    """
    Reduce an entity to its ID and schema
    """
    if not e.id:
        raise ValueError("Entity has no ID!")
    return EntityProxy.from_dict({"id": e.id, "schema": e.schema.name})


def make_checksum_entity(e: EntityProxy, quiet: bool | None = False) -> EntityProxy:
    """
    Reduce an entity to its ID, schema and contentHash property
    """
    q = bool(quiet)
    stub = make_stub_entity(e)
    stub.add("contentHash", e.get("contentHash", quiet=q), quiet=q)
    return stub
