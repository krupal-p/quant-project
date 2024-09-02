from app import log


def test_logger():
    log.debug("Debug")
    log.info("Info")
    log.warning("Warning")
    log.error("Error")
    log.critical("Critical")
