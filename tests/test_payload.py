import orjson

from openaleph_procrastinate.payload import pack_entities, unpack_entities
from openaleph_procrastinate.tasks import unpack_job


def test_pack_entities(fixtures_path):
    entities = [
        orjson.loads(line)
        for line in (fixtures_path / "eu_authorities.ftm.json")
        .read_bytes()
        .split(b"\n")
        if line
    ]
    packed = pack_entities(entities)
    assert isinstance(packed, str)
    assert len(packed) < len(orjson.dumps(entities)) / 2
    assert unpack_entities(packed) == entities


def test_unpack_plain_entities():
    # jobs deferred before entities were packed carry the plain list
    entities = [{"id": "a", "schema": "Thing"}]
    assert unpack_entities(entities) is entities


def test_unpack_job():
    entities = [{"id": "a", "schema": "Person", "properties": {"name": ["Jane"]}}]
    for value in (entities, pack_entities(entities)):
        job = unpack_job(
            {
                "dataset": "test",
                "queue": "q",
                "task": "t",
                "payload": {"entities": value, "context": {"foo": "bar"}},
            }
        )
        assert job.payload == {"entities": entities, "context": {"foo": "bar"}}
        assert [e.caption for e in job.get_entities()] == ["Jane"]
