"""
Logging estructurado para la aplicación usando stdlib.
"""
import logging
import sys

from .config import get_settings


def setup_logging(log_file: str | None = None) -> None:
    """
    Configura el sistema de logging.

    Args:
        log_file: Ruta opcional para archivo de log
    """
    settings = get_settings()

    # Configurar formato
    format_string = (
        "%(asctime)s | %(levelname)-8s | "
        "%(name)s:%(funcName)s:%(lineno)d | "
        "%(message)s"
    )

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(console_handler)

    # File handler si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S"))
        root_logger.addHandler(file_handler)

    # Configurar aiogram
    logging.getLogger("aiogram").setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para el módulo especificado.

    Args:
        name: Nombre del módulo (usualmente __name__)

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)
