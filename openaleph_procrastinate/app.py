from functools import cache

import procrastinate

from openaleph_procrastinate.settings import OpenAlephSettings


@cache
def make_app(tasks_module: str | None = None) -> procrastinate.App:
    settings = OpenAlephSettings()
    import_paths = [tasks_module] if tasks_module else None
    return procrastinate.App(
        connector=procrastinate.PsycopgConnector(
            conninfo=settings.db_uri,
        ),
        import_paths=import_paths,
    )


app = make_app()
