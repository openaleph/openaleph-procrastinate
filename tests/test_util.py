import pytest
from followthemoney import model

from openaleph_procrastinate import util


def test_util():
    e = model.make_entity("Document")
    e.id = "a"
    e.add("fileName", "test.txt")
    e.add("contentHash", "123")

    assert util.make_stub_entity(e).to_dict() == {
        "id": "a",
        "schema": "Document",
        "properties": {},
    }

    assert util.make_checksum_entity(e).to_dict() == {
        "id": "a",
        "schema": "Document",
        "properties": {"contentHash": ["123"]},
    }

    for i in ("", None):
        e.id = i
        with pytest.raises(ValueError):
            util.make_stub_entity(e)
        with pytest.raises(ValueError):
            util.make_checksum_entity(e)
