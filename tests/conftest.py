from pathlib import Path

import boto3
import pytest
from moto import mock_aws
from moto.server import ThreadedMotoServer

FIXTURES_PATH = (Path(__file__).parent / "fixtures").absolute()


@pytest.fixture(scope="session")
def fixtures_path():
    return FIXTURES_PATH


# http://docs.getmoto.org/en/latest/docs/server_mode.html
@pytest.fixture(scope="session", autouse=True)
def moto_server():
    """Fixture to run a mocked AWS server for testing."""
    server = ThreadedMotoServer(port=8888)
    server.start()
    host, port = server.get_host_and_port()
    setup_s3()
    yield f"http://{host}:{port}"
    server.stop()


@mock_aws
def setup_s3():
    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="openaleph")
