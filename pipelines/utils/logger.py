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
    Registra mensagens usando o logger do Prefect quando houver contexto ativo.

    Fora de um flow/task em execução, faz fallback para `print`.

    Args:
        *args: Partes da mensagem a serem registradas.
        level: Nível de severidade do log.
    """
    try:
        get_run_logger().log(LEVELS[level], " ".join(str(arg) for arg in args))
    except MissingContextError:
        print(*args)
