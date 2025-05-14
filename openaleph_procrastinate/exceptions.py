from openaleph_procrastinate import log_config
from openaleph_procrastinate.log_config import get_logger
from openaleph_procrastinate.settings import settings

log = get_logger(__name__)


class InvalidJob(Exception):
    pass


class ArchiveFileNotFound(Exception):
    pass


class EntityNotFound(Exception):
    pass


class ErrorHandler:
    def __init__(self, logger: log_config.BoundLogger | None = None) -> None:
        self.log = logger or log

    def __enter__(self):
        pass

    def __exit__(self, e, msg, _):
        if e is not None:
            if settings.debug:
                raise e
            self.log.error(f"{e.__name__}: {msg}")
