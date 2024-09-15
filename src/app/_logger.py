import logging
import logging.config
from pathlib import Path

from concurrent_log_handler import ConcurrentRotatingFileHandler

from app import config


def get_logger(log_dir: Path = config.LOG_DIR, logger_name: str = "app"):
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s] %(message)s",
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
                "maxBytes": 1000000,
            },
        },
        "root": {
            "level": config.LOG_LEVEL,
            "handlers": ["console", "info_file_handler"],
        },
    }

    log_dir = log_dir / "logs"

    if not log_dir.exists():
        log_dir.mkdir()

    log_config["handlers"]["info_file_handler"]["filename"] = str(
        log_dir / f"{logger_name}.log",
    )
    logging.config.dictConfig(log_config)

    return logging.getLogger(logger_name)


log = get_logger()
