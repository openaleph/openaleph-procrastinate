from functools import cache

import procrastinate
from anystore.logging import configure_logging, get_logger
from procrastinate import connector, testing, utils
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)


@cache
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
    configure_logging()
    import_paths = [tasks_module] if tasks_module else None
    connector = get_connector(sync=sync)
    log.info(
        "👋 I am the App!",
        connector=connector.__class__.__name__,
        sync=sync,
        tasks=tasks_module,
        module=__name__,
    )
    app = App(connector=connector, import_paths=import_paths)
    return app


def init_db() -> None:
    settings = OpenAlephSettings()
    log.info(f"Database `{settings.procrastinate_db_uri}`")
    if settings.in_memory_db:
        return
    app = make_app(sync=True)
    with app.open():
        db_ok = app.check_connection()
        if not db_ok:
            app.schema_manager.apply_schema()


def run_sync_worker(app: App) -> None:
    # used for testing. Make sure to use async connector
    app = make_app(list(app.import_paths)[0])
    app.run_worker(wait=False)
