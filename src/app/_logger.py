import logging
import logging.config
import threading
from typing import Any

from concurrent_log_handler import ConcurrentRotatingFileHandler  # noqa: F401

from app import config


@lambda _: _()
def setup_logging():
    """
    Initializes and configures the logging system for the application.

    This function sets up both console and rotating file handlers with a simple log format.
    It uses a thread lock to ensure thread-safe configuration. The file handler writes logs
    to a specified file with rotation based on file size and backup count. The configuration
    disables the removal of existing loggers and applies the settings using Python's
    logging configuration dictionary.

    Raises:
        Exception: If the logging configuration fails to apply.
    """

    print("Initializing logging configuration")
    lock = threading.Lock()
    with lock:
        _logging_config: dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "simple": {
                    "format": (
                        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] [%(module)s] %(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
                    "formatter": "simple",
                    "filename": str(config.LOG_DIR / "logs" / "app.log"),
                    "encoding": "utf8",
                    "backupCount": 5,
                    "maxBytes": int(1e6 * 10),  # 10MB
                },
            },
        }
        logging.config.dictConfig(_logging_config)


def get_logger(
    name: str = "app",
    level: str = config.LOG_LEVEL,
    handlers: list[str] | None = None,
) -> logging.Logger:
    """
    Creates and configures a logger instance with the specified name, logging level,
    and handlers.

    Args:
        name (str): The name of the logger. Defaults to "app".
        level (str): The logging level to set for the logger. Defaults to the value
            of `config.LOG_LEVEL`.
        handlers (list[str] | None): A list of handler names to attach to the logger.
            If None, defaults to ["console", "file"].

    Returns:
        logging.Logger: A configured logger instance.
    """
    if handlers is None:
        handlers = ["console", "file"]
    logger = logging.getLogger(name)
    logger.setLevel(level)

    existing_handler_names = {h.name for h in logger.handlers}
    for handler in handlers:
        if handler not in existing_handler_names:
            handler_instance = logging.getHandlerByName(handler)
            if handler_instance is not None:
                logger.addHandler(handler_instance)
    return logger


log = get_logger()
