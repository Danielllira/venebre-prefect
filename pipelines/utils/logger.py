import logging
from typing import Literal

from prefect.exceptions import MissingContextError
from prefect.logging import get_run_logger


LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def log(
    *args: object,
    level: Literal["debug", "info", "warning", "error", "critical"] = "info",
) -> None:
    """
    Logs messages using the Prefect logger when there is an active context.

    Outside a running flow/task, falls back to `print`.

    Args:
        *args: Parts of the message to be logged.
        level: Log severity level.
    """
    try:
        get_run_logger().log(LEVELS[level], " ".join(str(arg) for arg in args))
    except MissingContextError:
        print(*args)
