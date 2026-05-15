"""
Punto de entrada principal de RUTINATOR.
Inicializa configuración, logging y arranca el bot de Telegram.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.infrastructure.async_bridge import shutdown_executor
from src.infrastructure.config import get_settings
from src.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Inicializa y arranca el bot."""
    # 1. Configurar logging estructurado
    setup_logging()
    logger.info("Iniciando RUTINATOR...")

    # 2. Cargar configuración
    settings = get_settings()
    logger.info(f"Log level: {settings.log_level}")

    # 3. Importar router (carga lazy de servicios y repositorio)
    from src.bot_telegram import router

    # 4. Inicializar bot y dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot iniciado. Esperando mensajes...")

    try:
        await dp.start_polling(bot)
    finally:
        # 5. Apagar thread pool al cerrar
        shutdown_executor()
        await bot.session.close()
        logger.info("Bot detenido.")


if __name__ == "__main__":
    asyncio.run(main())
