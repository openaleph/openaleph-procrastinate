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

    uris = [
        (
            "postgresql://user:password@localhost:5432/mydb",
            "postgresql://***:***@localhost:5432/mydb",
        ),
        (
            "mysql://admin:secret@db.example.com:3306/app",
            "mysql://***:***@db.example.com:3306/app",
        ),
        (
            "sqlite://user:pass@/path/to/db.sqlite",
            "sqlite://***:***@/path/to/db.sqlite",
        ),
        (
            "oracle://dbuser:dbpass@oracle-server:1521/xe",
            "oracle://***:***@oracle-server:1521/xe",
        ),
        (
            "mongodb://username:password@mongo.example.com:27017/database",
            "mongodb://***:***@mongo.example.com:27017/database",
        ),
        (
            "redis://user:auth@redis.example.com:6379/0",
            "redis://***:***@redis.example.com:6379/0",
        ),
    ]

    for input_uri, expected_output in uris:
        assert util.mask_uri(input_uri) == expected_output

    # Test URIs without credentials (should remain unchanged)
    unchanged_uris = [
        "postgresql://localhost:5432/mydb",
        "mysql://db.example.com:3306/app",
        "sqlite:///path/to/db.sqlite",
    ]

    for uri in unchanged_uris:
        assert util.mask_uri(uri) == uri
