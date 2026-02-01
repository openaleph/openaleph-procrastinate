from anystore.logic.constants import SCHEME_FILE, SCHEME_S3
from anystore.util import ensure_uri
from moto import mock_aws
from servicelayer.archive import init_archive

from openaleph_procrastinate.archive import get_archive, lookup_key, make_checksum_key
from openaleph_procrastinate.helpers import get_localpath, open_file


@mock_aws
def test_archive(monkeypatch, tmp_path, fixtures_path):
    # local file
    path = str(tmp_path / "archive")
    monkeypatch.setenv("ARCHIVE_TYPE", "file")
    monkeypatch.setenv("ARCHIVE_PATH", path)
    archive = get_archive()
    assert archive.scheme == SCHEME_FILE
    assert archive.uri == ensure_uri(path)
    sl_archive = init_archive("file", path=path)
    checksum = sl_archive.archive_file(fixtures_path / "hello.txt")
    assert lookup_key(checksum) == f"{make_checksum_key(checksum)}/hello.txt"
    with get_localpath("", checksum) as p:
        assert str(p).endswith(f"{path}/{make_checksum_key(checksum)}/hello.txt")
        assert p.exists()
    # should still exist
    assert p.exists()

    with open_file("", checksum) as h:
        assert h.checksum == checksum
        assert h.read().decode().strip() == "world"
        assert str(h.path).endswith(f"{path}/{make_checksum_key(checksum)}/hello.txt")
        assert h.path.exists()
    # should still exist
    assert h.path.exists()

    # s3 (mocked)
    get_archive.cache_clear()
    monkeypatch.setenv("ARCHIVE_TYPE", "s3")
    monkeypatch.setenv("ARCHIVE_BUCKET", "openaleph")
    archive = get_archive()
    assert archive.scheme == SCHEME_S3
    sl_archive = init_archive("s3", bucket="openaleph")
    checksum = sl_archive.archive_file(fixtures_path / "hello.txt")
    assert lookup_key(checksum) == f"{make_checksum_key(checksum)}/data"

    with get_localpath("", checksum) as p:
        assert str(p).endswith(f"{make_checksum_key(checksum)}/data")
        assert str(p).startswith("/tmp")
        assert p.exists()
    # should not exist anymore
    assert not p.exists()

    with open_file("", checksum) as h:
        assert h.checksum == checksum
        assert h.read().decode().strip() == "world"
        assert str(h.path).startswith("/tmp")
    # should not exist anymore
    assert not h.path.exists()
