import logging
import logging.config
import threading

from concurrent_log_handler import ConcurrentRotatingFileHandler

from app import config


class Logger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                cls.log_config = {
                    "version": 1,
                    "disable_existing_loggers": True,
                    "formatters": {
                        "simple": {
                            "format": "[%(asctime)s] [%(levelname)s] [%(process)d] [%(module)s] %(message)s",
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
                            "encoding": "utf8",
                            "backupCount": 5,
                            "maxBytes": 1e6 * 10,
                        },
                    },
                    "root": {
                        "level": config.LOG_LEVEL,
                        "handlers": ["console", "info_file_handler"],
                    },
                }

                log_dir = config.LOG_DIR / "logs"

                if not log_dir.exists():
                    log_dir.mkdir()

                cls.log_config["handlers"]["info_file_handler"]["filename"] = str(
                    log_dir / "app.log",
                )
                logging.config.dictConfig(cls.log_config)

                cls.log = logging.getLogger("app")
        return cls._instance


log: logging.Logger = Logger().log
