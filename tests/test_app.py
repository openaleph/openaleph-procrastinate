import asyncio
import os
import socket
import subprocess
import sys

import pytest

from openaleph_procrastinate.app import SharedPoolConnector

# The server accepts connections but never answers the handshake, so the pool
# tasks are busy connecting when the process wants to exit
EXIT_SCRIPT = """
import asyncio
from openaleph_procrastinate.app import make_app

async def main():
    try:
        async with asyncio.timeout(0.5):
            async with make_app().open_async():
                raise AssertionError("Silent server must not yield a connection")
    except TimeoutError:
        print("app closed", flush=True)

asyncio.run(main())
"""


class DummyPool:
    def __init__(self, fail: bool = False, **kwargs):
        self.fail = fail
        self.closed = False

    async def open(self, wait: bool = False):
        await asyncio.sleep(0)
        if self.fail:
            raise RuntimeError("Can't connect")

    async def close(self):
        await asyncio.sleep(0)
        self.closed = True


def test_app_process_exits_without_database():
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        env = {
            **os.environ,
            "DEBUG": "0",
            "PROCRASTINATE_DB_URI": f"postgresql://u:p@127.0.0.1:{port}/db",
        }
        res = subprocess.run(
            [sys.executable, "-c", EXIT_SCRIPT],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert res.returncode == 0, res.stderr
    assert "app closed" in res.stdout


def test_app_pool_closed_with_last_user():
    async def run():
        connector = SharedPoolConnector(pool_factory=DummyPool)
        await connector.open_async()
        pool = connector.pool
        await connector.open_async()
        assert connector.pool is pool

        await connector.close_async()
        assert connector.pool is pool
        assert not pool.closed

        # opening while the last user is closing gets a new pool
        await asyncio.gather(connector.close_async(), connector.open_async())
        assert pool.closed
        assert connector.pool is not pool
        assert not connector.pool.closed

        pool = connector.pool
        await connector.close_async()
        assert pool.closed
        # closing too often doesn't confuse the next user
        await connector.close_async()
        await connector.open_async()
        assert not connector.pool.closed

    asyncio.run(run())


def test_app_pool_closed_on_failed_open():
    async def run():
        pools = []

        def pool_factory(**kwargs):
            pools.append(DummyPool(fail=not pools))
            return pools[-1]

        connector = SharedPoolConnector(pool_factory=pool_factory)
        with pytest.raises(RuntimeError):
            await connector.open_async()
        assert pools[0].closed

        # the failed attempt doesn't count as a user
        await connector.open_async()
        assert connector.pool is pools[1]
        await connector.close_async()
        assert pools[1].closed

    asyncio.run(run())


def test_app_pool_from_caller_stays_open():
    async def run():
        pool = DummyPool()
        connector = SharedPoolConnector(pool_factory=DummyPool)
        await connector.open_async(pool)
        await connector.close_async()
        assert not pool.closed

    asyncio.run(run())
