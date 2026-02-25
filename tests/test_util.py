from followthemoney import model

from openaleph_procrastinate import util


def test_util():
    e = model.make_entity("Document")
    e.id = "a"
    e.add("fileName", "test.txt")
    e.add("contentHash", "123")
    e.add("parent", "1")

    assert util.make_stub_entity(e).to_dict() == {
        "caption": "test.txt",
        "id": "a",
        "schema": "Document",
        "properties": {},
        "datasets": ["default"],
        "referents": [],
    }

    assert util.make_file_entity(e).to_dict() == {
        "caption": "test.txt",
        "id": "a",
        "schema": "Document",
        "properties": {
            "contentHash": ["123"],
            "fileName": ["test.txt"],
            "parent": ["1"],
        },
        "datasets": ["default"],
        "referents": [],
    }

    for i in ("", None):
        e.id = i
        assert util.make_stub_entity(e) is None
        assert util.make_file_entity(e) is None
