"""
Puente async/sync para ejecutar operaciones bloqueantes en thread pool.
Garantiza que el event loop de aiogram nunca se bloquee.
"""
import asyncio
import io
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import Any

logger = logging.getLogger(__name__)

# Thread pool compartido para operaciones de I/O bloqueantes
_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    """Obtiene el executor compartido."""
    global _executor
    if _executor is None:
        # Crear executor con线程 mínima para no bloquear
        _executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="rutinator_io",
        )
        logger.info("ThreadPoolExecutor inicializado")
    return _executor


def run_in_executor(sync_func: Callable[..., Any]) -> Callable[..., asyncio.Future]:
    """
    Decorador que envuelve una función síncrona para ejecutarse en thread pool.

    Usage:
        @run_in_executor
        def blocking_function():
            # operaciones bloqueantes (pandas, matplotlib, reportlab)
            return result

    En el handler async:
        result = await blocking_function()
    """
    @wraps(sync_func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop()
        executor = get_executor()

        # Usar partial para preservar argumentos
        func = partial(sync_func, *args, **kwargs)

        # Ejecutar en thread pool
        result = await loop.run_in_executor(executor, func)
        return result

    return async_wrapper


async def run_sync_in_thread(func: Callable[..., Any]) -> Any:
    """
    Ejecuta una función síncrona en el thread pool.

    Args:
        func: Función síncrona a ejecutar

    Returns:
        Resultado de la función
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(get_executor(), func)


class AsyncPDFGenerator:
    """
    Wrapper para generar PDFs de forma asíncrona.

    Envuelve las funciones síncronas de generación de PDF
    y las ejecuta en thread pool.
    """

    def __init__(self) -> None:
        self._executor = get_executor()

    async def generate_rutina_completa(
        self,
        datos_usuario: dict,
    ) -> "io.BytesIO":
        """Genera PDF de rutina completa de forma asíncrona."""
        from src.infrastructure.generators.pdf_rutina import generar_pdf_rutina_sync

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            generar_pdf_rutina_sync,
            datos_usuario,
        )

    async def generate_rutina_semanal(
        self,
        datos_usuario: dict,
    ) -> "io.BytesIO":
        """Genera PDF de rutina semanal con feedback de forma asíncrona."""
        from src.infrastructure.generators.pdf_semanal import generar_rutina_semanal_sync

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            generar_rutina_semanal_sync,
            datos_usuario,
        )

    async def generate_revista_nutricional(
        self,
        datos_usuario: dict,
    ) -> "io.BytesIO":
        """Genera PDF de revista nutricional de forma asíncrona."""
        from src.infrastructure.generators.pdf_nutricion import generar_revista_nutricional_sync

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            generar_revista_nutricional_sync,
            datos_usuario,
        )


# Instancia global
_async_pdf_generator: AsyncPDFGenerator | None = None


def get_async_pdf_generator() -> AsyncPDFGenerator:
    """Obtiene instancia singleton del generador async de PDFs."""
    global _async_pdf_generator
    if _async_pdf_generator is None:
        _async_pdf_generator = AsyncPDFGenerator()
    return _async_pdf_generator


def shutdown_executor() -> None:
    """Apaga el executor (llamar al cerrar la aplicación)."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("ThreadPoolExecutor detenido")
