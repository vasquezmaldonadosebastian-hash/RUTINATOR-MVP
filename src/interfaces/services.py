"""
Servicios de interfaz - Glue entre handlers y aplicación.
Provee métodos async que usan el async_bridge para operaciones bloqueantes.
"""
import io
import logging
from typing import Any

from src.application import get_training_generator_service
from src.infrastructure.async_bridge import get_async_pdf_generator

logger = logging.getLogger(__name__)


class InterfaceService:
    """
    Servicio de interfaz para el bot.

    Maneja la generación de programas y PDFs de forma asíncrona,
    usando el thread pool para operaciones bloqueantes.
    """

    def __init__(self) -> None:
        self._generator = get_training_generator_service()
        self._pdf = get_async_pdf_generator()

    async def generar_programa_async(self, datos: dict[str, Any]) -> dict[str, Any]:
        """
        Genera programa de forma asíncrona.

        Args:
            datos: Diccionario con datos del atleta

        Returns:
            Programa en formato dict
        """
        # Usar el servicio existente que ya tiene el método
        programa = self._generator.generar_programa_desde_dict(datos)
        return programa.model_dump()

    async def generar_pdf_rutina_completa_async(
        self,
        datos: dict[str, Any],
    ) -> io.BytesIO:
        """
        Genera PDF de rutina completa de forma asíncrona.

        Args:
            datos: Diccionario con datos del atleta

        Returns:
            BytesIO con el PDF
        """
        return await self._pdf.generate_rutina_completa(datos)

    async def generar_pdf_rutina_semanal_async(
        self,
        datos: dict[str, Any],
    ) -> io.BytesIO:
        """
        Genera PDF de rutina semanal de forma asíncrona.

        Args:
            datos: Diccionario con datos del atleta

        Returns:
            BytesIO con el PDF
        """
        return await self._pdf.generate_rutina_semanal(datos)

    async def generar_pdf_nutricion_async(
        self,
        datos: dict[str, Any],
    ) -> io.BytesIO:
        """
        Genera PDF de revista nutricional de forma asíncrona.

        Args:
            datos: Diccionario con datos del atleta

        Returns:
            BytesIO con el PDF
        """
        return await self._pdf.generate_revista_nutricional(datos)

    def formatear_resumen(self, datos: dict[str, Any]) -> str:
        """
        Formatea un resumen de los datos del atleta.

        Args:
            datos: Diccionario con datos del atleta

        Returns:
            String con el resumen formateado
        """
        return (
            f"✅ *PLAN CREADO CON ÉXITO*\n\n"
            f"*Atleta:* {datos.get('atleta', 'No definido')}\n"
            f"*Objetivo:* {datos.get('objetivo', 'No definido')}\n"
            f"*Nivel:* {datos.get('nivel', 'No definido')}\n"
            f"*Edad/Sexo:* {datos.get('edad', 'No definido')} años / {datos.get('sexo', 'No definido')}\n"
            f"*Peso/Talla:* {datos.get('peso', 'No definido')} kg / {datos.get('talla', 'No definido')} cm\n"
            f"*Equipamiento:* {datos.get('equipamiento', 'No definido')}\n"
            f"*Días/semana:* {datos.get('dias_semana', 'No definido')}\n"
            f"*Lesiones:* {datos.get('lesiones', 'Ninguna')}\n\n"
            f"*Comandos disponibles:*\n"
            f"`/rutinasemanal` - Generar rutina semanal con feedback\n"
            f"`/nutricion` - Generar revista nutricional editorial\n"
            f"`/verdatos` - Ver estos datos nuevamente"
        )

    def formatear_datos_actuales(self, data: dict[str, Any]) -> str:
        """Formatea los datos actuales para mostrar al usuario."""
        if not data:
            return "📭 *No hay datos de atleta almacenados.*\nUsa `/nuevoplan` para comenzar."

        info = (
            f"*📊 DATOS DEL ATLETA ACTUAL*\n\n"
            f"• *Nombre:* {data.get('atleta', 'No definido')}\n"
            f"• *Objetivo:* {data.get('objetivo', 'No definido')}\n"
            f"• *Nivel:* {data.get('nivel', 'No definido')}\n"
            f"• *Edad:* {data.get('edad', 'No definido')}\n"
            f"• *Sexo:* {data.get('sexo', 'No definido')}\n"
            f"• *Peso:* {data.get('peso', 'No definido')} kg\n"
            f"• *Talla:* {data.get('talla', 'No definido')} cm\n"
            f"• *Equipamiento:* {data.get('equipamiento', 'No definido')}\n"
            f"• *Días/semana:* {data.get('dias_semana', 'No definido')}\n"
            f"• *Lesiones:* {data.get('lesiones', 'Ninguna')}\n"
        )
        return info


# Instancia singleton
_interface_service: InterfaceService | None = None


def get_interface_service() -> InterfaceService:
    """Obtiene instancia singleton del servicio de interfaz."""
    global _interface_service
    if _interface_service is None:
        _interface_service = InterfaceService()
    return _interface_service
