import logging
import logging.config
import threading
from typing import Any

from concurrent_log_handler import ConcurrentRotatingFileHandler  # type: ignore

from app import config


class Logger:
    """
    Logger is a thread-safe singleton class responsible for configuring and managing the application's logging setup.

    This class ensures that only one instance of the logger is created and shared across the application. It uses a lock
    to synchronize threads during the first instantiation and prevents reinitialization of the logger configuration.

    Methods:
        __new__(cls):
            Ensures that only one instance of the Logger class is created (singleton pattern).
        __init__():
            Initializes the logger configuration if it hasn't been initialized already.
        _setup_logging_config():
            Configures the logging settings, including formatters, handlers, and log file rotation.

    Attributes:
        _instance (Logger or None):
            Holds the singleton instance of the Logger class.
        _lock (threading.Lock):
            A lock object to synchronize threads during the first instantiation.
        _initialized (bool):
            A flag to prevent reinitialization of the logger configuration.
    """

    _instance = None
    _lock = threading.Lock()  # Lock to synchronize threads during first instantiation.

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Another thread could have created the instance
                # before we acquired the lock. So check that the
                # instance is still nonexistent.
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent reinitialization if __init__ gets called multiple times.
        if not getattr(self, "_initialized", False):
            self._setup_logging_config()
            self._initialized = True

    def _setup_logging_config(self) -> None:
        """Configure and set up the logger"""
        print("Setting up logging configuration")
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
    Logger()
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
