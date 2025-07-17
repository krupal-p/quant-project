def test_logger():
    from app import log

    log.debug("Debug")
    log.info("Info")
    log.warning("Warning")
    log.error("Error")
    log.critical("Critical")
