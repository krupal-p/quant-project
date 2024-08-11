import logging
import logging.config
from pathlib import Path

from qp import config


class Logger:
    def __init__(self, log_dir) -> None:
        self.log_config = {
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
                    "class": "logging.FileHandler",
                    "formatter": "simple",
                    "encoding": "utf8",
                },
            },
            "root": {
                "level": config.LOG_LEVEL,
                "handlers": ["console", "info_file_handler"],
            },
        }
        self.log_dir = log_dir / "logs"

        if not self.log_dir.exists():
            self.log_dir.mkdir()

    def get_logger(self, logger_name: str) -> logging.Logger:
        self.log_config["handlers"]["info_file_handler"]["filename"] = str(
            self.log_dir / f"{logger_name}.log",
        )
        logging.config.dictConfig(self.log_config)

        return logging.getLogger(logger_name)


log: logging.Logger = Logger(Path(__file__).parent).get_logger("qp")

if __name__ == "__main__":
    log.debug("Hello World")
    log.info("Hello World")
    log.warning("Hello World")
    log.error("Hello World")
    log.critical("Hello World")
