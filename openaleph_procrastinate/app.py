import threading

import procrastinate
from anystore.functools import weakref_cache as cache
from anystore.logging import configure_logging, get_logger
from anystore.util import mask_uri
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from procrastinate import connector, testing, utils
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)

# Thread-safe cache for get_pool function
_pool_cache = TTLCache(maxsize=10, ttl=3600)  # 1 hour TTL
_pool_cache_lock = threading.RLock()


@cached(cache=_pool_cache, lock=_pool_cache_lock, key=lambda sync=False: hashkey(sync))
def get_pool(sync: bool | None = False) -> ConnectionPool | AsyncConnectionPool | None:
    settings = OpenAlephSettings()
    if settings.in_memory_db:
        return
    if sync:
        return ConnectionPool(
            settings.procrastinate_db_uri, min_size=1, max_size=settings.db_pool_size
        )
    return AsyncConnectionPool(
        settings.procrastinate_db_uri, min_size=1, max_size=settings.db_pool_size
    )


class App(procrastinate.App):
    def open(
        self, pool_or_engine: connector.Pool | connector.Engine | None = None
    ) -> procrastinate.App:
        """Use a shared connection pool by default if not provided"""
        if pool_or_engine is None:
            pool_or_engine = get_pool(sync=True)
        return super().open(pool_or_engine)

    def open_async(self, pool: connector.Pool | None = None) -> utils.AwaitableContext:
        """Use a shared connection pool by default if not provided"""
        if pool is None:
            pool = get_pool()
        return super().open_async(pool)


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
    return procrastinate.PsycopgConnector(conninfo=db_uri)


@cache
def make_app(tasks_module: str | None = None, sync: bool | None = False) -> App:
    settings = OpenAlephSettings()
    db_uri = mask_uri(settings.procrastinate_db_uri)
    configure_logging()
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
