from anystore.logging import get_logger
from structlog import BoundLogger

from openaleph_procrastinate.settings import OpenAlephSettings

settings = OpenAlephSettings()
log = get_logger(__name__)


class InvalidJob(Exception):
    pass


class ArchiveFileNotFound(Exception):
    pass


class ErrorHandler:
    def __init__(self, logger: BoundLogger | None = None) -> None:
        self.log = logger or log

    def __enter__(self):
        pass

    def __exit__(self, e, msg, _):
        if e is not None:
            if settings.debug:
                raise e
            self.log.error(f"{e.__name__}: {msg}")
