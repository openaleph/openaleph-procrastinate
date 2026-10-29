"""
Job payload entities are stored as a zstd compressed orjson string instead of a
jsonb tree. procrastinate keeps the job args as `jsonb`, and a large entities
tree in there costs postgres parsing, pglz (de-)compression, WAL and table size
on every defer, fetch and status update. Only `payload.entities` is packed, the
rest of the args stays plain jsonb (the `dataset` and `batch` columns are
generated from it).

jsonb can't hold bytes, so the compressed frame is base64 encoded.
"""

import base64
from io import BytesIO
from typing import Any, TypeAlias, cast

import orjson
from anystore.logic.compress import CompressKind, open_codec

Entities: TypeAlias = list[dict[str, Any]]


def pack_entities(entities: Entities) -> str:
    """Serialize entity dicts into a compressed string for the job payload"""
    buf = BytesIO()
    with open_codec(buf, CompressKind.zst, "wb") as fh:
        fh.write(orjson.dumps(entities))
    return base64.b64encode(buf.getvalue()).decode()


def unpack_entities(entities: str | Entities) -> Entities:
    """Load entity dicts from the job payload. A plain list (a job deferred
    before entities were packed) passes through."""
    if not isinstance(entities, str):
        return entities
    data = BytesIO(base64.b64decode(entities))
    with open_codec(data, CompressKind.zst, "rb") as fh:
        return cast(Entities, orjson.loads(fh.read()))
