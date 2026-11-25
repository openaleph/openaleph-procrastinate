import threading
from functools import cache
from typing import Any

import procrastinate
from anystore.logging import configure_logging, get_logger
from anystore.util import mask_uri
from cachetools import TTLCache, cached
from procrastinate import connector, testing
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from openaleph_procrastinate.logging import patch_procrastinate_logging
from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)

# Thread-safe cache for get_sync_pool function
_pool_cache = TTLCache(maxsize=10, ttl=3600)  # 1 hour TTL
_pool_cache_lock = threading.RLock()


def get_pool_config() -> dict[str, Any]:
    """
    Get the psycopg connection pool configuration for long-running workers.

    CRITICAL: psycopg3 does NOT check connection health by default!
    From the docs: "The pool doesn't actively check the state of the connections
    held in its state. This means that [...] the application might be served a
    connection in broken state."

    Without proper configuration, workers will hang after idle periods when they
    receive stale/dead connections from the pool. This manifests as:
    - Workers stop processing jobs after 10-60 minutes
    - Active PostgreSQL connections drop to 0
    - Workers appear "hung" but are actually waiting for usable connections

    Configuration rationale:
    - max_idle=300s (5min)
      Pool proactively closes connections before PostgreSQL kills them
    - check=ConnectionPool.check_connection is ESSENTIAL
      Even with max_idle, connections can die from network issues, restarts, etc.
      Without this, workers get broken connections and hang. It is not part of
      this config as procrastinate already sets it for the pools it creates.
    - timeout=30s prevents infinite hangs if pool can't get a connection
    - max_lifetime=3600s forces periodic connection refresh

    See: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
    """
    settings = OpenAlephSettings()
    return {
        "min_size": 1,
        "max_size": settings.db_pool_size,
        "max_idle": 300,
        "max_lifetime": 3600,
        "timeout": 30,
    }


@cached(cache=_pool_cache, lock=_pool_cache_lock)
def get_sync_pool() -> ConnectionPool | None:
    """Get the shared pool for sync connections"""
    settings = OpenAlephSettings()
    if settings.in_memory_db:
        return None
    return ConnectionPool(
        settings.procrastinate_db_uri,
        check=ConnectionPool.check_connection,
        **get_pool_config(),
    )


class SharedPoolConnector(procrastinate.PsycopgConnector):
    """
    Close the async pool when its last user is done.

    This connector is shared by all apps within a process, so closing one app
    must not close the pool others still use. But the pool can't be left open
    either: its maintenance tasks swallow the cancellation `asyncio.run()` sends
    them on shutdown, which would then wait for them forever.

    Pools passed in by the caller are never closed.
    """

    _users: int = 0

    async def open_async(self, pool: AsyncConnectionPool | None = None) -> None:
        self._users += 1
        try:
            await super().open_async(pool)
        except BaseException:  # including cancellation
            await self.close_async()
            raise

    async def close_async(self) -> None:
        self._users = max(self._users - 1, 0)
        if self._users or self._async_pool is None or self._pool_externally_set:
            return
        # detach first: opening again while this closes needs a new pool
        pool, self._async_pool = self._async_pool, None
        await pool.close()


class App(procrastinate.App):
    def open(
        self, pool_or_engine: connector.Pool | connector.Engine | None = None
    ) -> procrastinate.App:
        """Use a shared connection pool by default if not provided"""
        if pool_or_engine is None:
            pool_or_engine = get_sync_pool()
        return super().open(pool_or_engine)


@cache
def in_memory_connector() -> testing.InMemoryConnector:
    # cache globally to share in async / sync context
    return testing.InMemoryConnector()


@cache
def get_connector(sync: bool | None = False) -> connector.BaseConnector:
    settings = OpenAlephSettings()
    if settings.in_memory_db:
        # https://procrastinate.readthedocs.io/en/stable/howto/production/testing.html
        return in_memory_connector()
    db_uri = settings.procrastinate_db_uri
    if sync:
        return procrastinate.SyncPsycopgConnector(conninfo=db_uri)
    return SharedPoolConnector(conninfo=db_uri, **get_pool_config())


@cache
def make_app(tasks_module: str | None = None, sync: bool | None = False) -> App:
    settings = OpenAlephSettings()
    db_uri = mask_uri(settings.procrastinate_db_uri)
    configure_logging()
    patch_procrastinate_logging()
    import_paths = [tasks_module] if tasks_module else None
    connector = get_connector(sync=sync)
    log.info(
        "👋 I am the App!",
        connector=connector.__class__.__name__,
        sync=sync,
        tasks=tasks_module,
        module=__name__,
        db_uri=db_uri,
    )
    app = App(connector=connector, import_paths=import_paths)
    return app


def run_sync_worker(app: App) -> None:
    # used for testing. Force using async connector with re-initializing app:
    app = make_app(list(app.import_paths)[0])
    app.run_worker(wait=False)
