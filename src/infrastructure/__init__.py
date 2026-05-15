"""Infrastructure layer - Configuration, logging, repositories, async bridge."""
from .async_bridge import (
    AsyncPDFGenerator,
    get_async_pdf_generator,
    run_in_executor,
    run_sync_in_thread,
    shutdown_executor,
)
from .config import get_settings, settings
from .logging import get_logger, setup_logging
from .repositories.exercise_repository import ExerciseRepository, get_exercise_repository

__all__ = [
    # Config
    "get_settings",
    "settings",
    # Logging
    "get_logger",
    "setup_logging",
    # Repositories
    "ExerciseRepository",
    "get_exercise_repository",
    # Async bridge
    "AsyncPDFGenerator",
    "get_async_pdf_generator",
    "run_in_executor",
    "run_sync_in_thread",
    "shutdown_executor",
]
