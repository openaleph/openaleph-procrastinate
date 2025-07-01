from functools import cache
from typing import Self

import procrastinate
from anystore.logging import configure_logging, get_logger
from procrastinate import connector, testing

from openaleph_procrastinate.settings import OpenAlephSettings

log = get_logger(__name__)


class App(procrastinate.App):
    """
    Not sure if this is a good idea.

    [Originally, the app needs to be opened and closed
    explicitly](https://procrastinate.readthedocs.io/en/stable/howto/basics/open_connection.html)

    As we are deferring tasks synchronously within an async procrastinate worker
    context, this run into connection issues when opening and closing the app
    too frequently. So we keep it open. This will definitely backfire at one
    point and needs more postgresql connection tweaking within this app.
    """

    _is_open = False

    def open(self, *args, **kwargs) -> Self | procrastinate.App:
        if not self._is_open:
            self._is_open = True
            return super().open(*args, **kwargs)
        return self

    def __exit__(self, *args, **kwargs) -> None:
        # don't close
        pass


@cache
def get_connector(sync: bool | None = False) -> connector.BaseConnector:
    settings = OpenAlephSettings()
    if settings.debug:
        # https://procrastinate.readthedocs.io/en/stable/howto/production/testing.html
        return testing.InMemoryConnector()
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


app = make_app()
