import procrastinate

from openaleph_procrastinate.settings import settings


def make_app(tasks_module: str) -> procrastinate.App:
    return procrastinate.App(
        connector=procrastinate.PsycopgConnector(
            conninfo=settings.db_uri,
        ),
        import_paths=[tasks_module],
    )


app = make_app("openaleph_procrastinate.tasks")
