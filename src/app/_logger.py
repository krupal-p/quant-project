import logging
import logging.config
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from concurrent_log_handler import ConcurrentRotatingFileHandler

from app import config


@dataclass
class LogConfig:
    """Configuration settings for logging"""

    max_bytes: int = int(1e6 * 10)  # 10MB
    backup_count: int = 5
    encoding: str = "utf8"
    log_format: str = (
        "[%(asctime)s] [%(levelname)s] [%(process)d] [%(module)s] %(message)s"
    )


class Logger:
    """Thread-safe singleton logger implementation"""

    _instance: Optional["Logger"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._setup_logger()
                    self._initialized = True

    def _setup_logger(self) -> None:
        """Configure and set up the logger"""
        log_config = LogConfig()
        log_dir = self._create_log_directory()

        self.log_config: dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "simple": {
                    "format": log_config.log_format,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                },
                "info_file_handler": {
                    "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
                    "formatter": "simple",
                    "filename": str(log_dir / "app.log"),
                    "encoding": log_config.encoding,
                    "backupCount": log_config.backup_count,
                    "maxBytes": log_config.max_bytes,
                },
            },
            "root": {
                "level": config.LOG_LEVEL,
                "handlers": ["console", "info_file_handler"],
            },
        }

        try:
            logging.config.dictConfig(self.log_config)
            self.log = logging.getLogger("app")
        except Exception as e:
            msg = f"Failed to initialize logger: {e!s}"
            raise RuntimeError(msg) from e

    @staticmethod
    def _create_log_directory() -> Path:
        """Create and return the log directory"""
        log_dir = config.LOG_DIR / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            msg = f"Failed to create log directory: {e!s}"
            raise RuntimeError(msg) from e
        else:
            return log_dir


# Global logger instance
log: logging.Logger = Logger().log
