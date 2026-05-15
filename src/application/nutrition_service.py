"""
Servicio de nutrición y generación de planes nutricionales.
"""
import logging

from src.domain.models import Macros, NutricionPlan
from src.domain.rules import (
    calcular_macros,
    generar_estrategia_nutricional,
    generar_estrategias_neat,
    generar_intro_neat,
)

logger = logging.getLogger(__name__)


class NutritionService:
    """
    Servicio de nutrición.

    Calcula macros, genera estrategias nutricionales y planes
    personalizados según el objetivo del atleta.
    """

    def calcular_macros(
        self,
        objetivo: str,
        peso_kg: float,
    ) -> Macros:
        """
        Calcula macronutrientes según objetivo y peso.

        Args:
            objetivo: Objetivo del entrenamiento
            peso_kg: Peso del atleta en kg

        Returns:
            Macros calculados con gramos y porcentajes
        """
        return calcular_macros(objetivo, peso_kg)

    def generar_plan_nutricional(
        self,
        objetivo: str,
        peso_kg: float,
    ) -> NutricionPlan:
        """
        Genera plan nutricional completo.

        Args:
            objetivo: Objetivo del entrenamiento
            peso_kg: Peso del atleta en kg

        Returns:
            NutricionPlan con estrategia y recomendaciones
        """
        macros = self.calcular_macros(objetivo, peso_kg)
        return generar_estrategia_nutricional(objetivo, macros)

    def generar_info_neat(
        self,
        objetivo: str,
    ) -> tuple[str, list[str]]:
        """
        Genera información sobre NEAT (Non-Exercise Activity Thermogenesis).

        Args:
            objetivo: Objetivo del entrenamiento

        Returns:
            Tupla (introducción, lista de estrategias)
        """
        intro = generar_intro_neat(objetivo)
        estrategias = generar_estrategias_neat()
        return intro, estrategias


# Instancia singleton
_nutrition_service: NutritionService | None = None


def get_nutrition_service() -> NutritionService:
    """Obtiene instancia singleton del servicio."""
    global _nutrition_service
    if _nutrition_service is None:
        _nutrition_service = NutritionService()
    return _nutrition_service
