"""统一日志配置"""
import logging
import sys


def _make_logger() -> logging.Logger:
    log = logging.getLogger("growth_os")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    log.addHandler(handler)
    return log


logger = _make_logger()
