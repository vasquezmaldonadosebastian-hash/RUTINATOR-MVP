"""
Servicio principal de generación de programas.
Orquesta todos los servicios (periodización, nutrición, biometría).
"""
import logging
from dataclasses import dataclass

from src.application.nutrition_service import get_nutrition_service
from src.application.periodization_service import get_periodization_service
from src.domain.models import (
    Athlete,
    Biometria,
    GastoEnergetico,
    ProgramaCompleto,
)
from src.domain.rules import (
    calcular_gasto,
    calcular_imc,
    estimar_agua,
    estimar_grasa,
)

logger = logging.getLogger(__name__)


@dataclass
class AthleteData:
    """Datos crudos del atleta desde el frontend."""
    nombre: str
    objetivo: str
    nivel: str
    edad: int
    sexo: str
    peso: float
    talla: float
    equipamiento: str
    dias_semana: int
    lesiones: str = "Ninguna"
    deporte_paralelo: str = "Ninguno"


class TrainingGeneratorService:
    """
    Servicio principal de generación de programas.

    Orquesta la generación completa de un programa de entrenamiento:
    - Datos del atleta (validados)
    - Biometría (IMC, grasa, agua)
    - Macros y gasto energético
    - Periodización ATR
    - Plan nutricional
    """

    def __init__(self) -> None:
        self._periodization = get_periodization_service()
        self._nutrition = get_nutrition_service()

    def generar_programa_completo(
        self,
        datos: AthleteData,
        semana: int | None = None,
    ) -> ProgramaCompleto:
        """
        Genera programa completo para un atleta.

        Args:
            datos: Datos del atleta
            semana: Semana específica (None = 12 semanas)

        Returns:
            ProgramaCompleto con todos los datos
        """
        logger.info(f"Generando programa para {datos.nombre}, objetivo: {datos.objetivo}")

        # 1. Crear modelo de atleta
        athlete = self._crear_athlete(datos)

        # 2. Calcular biometría
        biometria = self._calcular_biometria(
            datos.peso, datos.talla, datos.edad, datos.sexo
        )

        # 3. Calcular macros
        macros = self._nutrition.calcular_macros(datos.objetivo, datos.peso)

        # 4. Calcular gasto energético
        gasto = self._nutrition_generar_gasto(datos.nivel)

        # 5. Generar periodización
        semanas = self._periodization.generar_programa(
            nivel=datos.nivel,
            objetivo=datos.objetivo,
            lesiones=datos.lesiones,
            equipamiento=datos.equipamiento,
            dias_semana=datos.dias_semana,
            semana=semana,
        )

        # 6. Generar plan nutricional
        nutricion = self._nutrition.generar_plan_nutricional(
            datos.objetivo, datos.peso
        )

        # 7. Armar programa completo
        programa = ProgramaCompleto(
            athlete=athlete,
            biometria=biometria,
            macros=macros,
            gasto=gasto,
            nutricion=nutricion,
            semanas=semanas,
            meta={
                "generado_en": "RUTINATOR v2.0",
                "semanas_generadas": len(semanas),
            },
        )

        logger.info(f"Programa generado exitosamente: {len(semanas)} semanas")
        return programa

    def generar_programa_desde_dict(
        self,
        datos_dict: dict,
    ) -> ProgramaCompleto:
        """
        Genera programa desde dict (compatibilidad con bot actual).

        Args:
            datos_dict: Diccionario con datos del atleta

        Returns:
            ProgramaCompleto
        """
        datos = AthleteData(
            nombre=datos_dict.get("atleta", "Atleta"),
            objetivo=datos_dict.get("objetivo", "Recomposición"),
            nivel=datos_dict.get("nivel", "Principiante"),
            edad=int(datos_dict.get("edad", 25)),
            sexo=datos_dict.get("sexo", "Masculino"),
            peso=float(str(datos_dict.get("peso", 70)).replace(",", ".")),
            talla=float(str(datos_dict.get("talla", 170)).replace(",", ".")),
            equipamiento=datos_dict.get("equipamiento", "Gimnasio completo"),
            dias_semana=int(datos_dict.get("dias_semana", 3)),
            lesiones=datos_dict.get("lesiones", "Ninguna"),
            deporte_paralelo=datos_dict.get("deporte_paralelo", "Ninguno"),
        )

        semana = datos_dict.get("semana_actual")
        return self.generar_programa_completo(datos, semana)

    def _crear_athlete(self, datos: AthleteData) -> Athlete:
        """Crea modelo Athlete desde datos crudos."""
        # Mapear strings a enums
        from src.domain.models import Equipamiento, Nivel, Objetivo, Sexo

        objetivo_map = {
            "quemar grasa": Objetivo.QUEMAR_GRASA,
            "ganar músculo": Objetivo.GANAR_MUSCULO,
            "ganar musculo": Objetivo.GANAR_MUSCULO,
            "recomposición": Objetivo.RECOMPOSICION,
            "recompostura": Objetivo.RECOMPOSICION,
        }

        nivel_map = {
            "principiante": Nivel.PRINCIPIANTE,
            "intermedio": Nivel.INTERMEDIO,
            "avanzado": Nivel.AVANZADO,
        }

        sexo_map = {
            "masculino": Sexo.MASCULINO,
            "hombre": Sexo.MASCULINO,
            "femenino": Sexo.FEMENINO,
            "mujer": Sexo.FEMENINO,
        }

        equipo_map = {
            "gimnasio completo": Equipamiento.GIMNASIO_COMPLETO,
            "casa con mancuernas": Equipamiento.CASA_CON_MANCUERNAS,
            "peso corporal": Equipamiento.PESO_CORPORAL,
        }

        objetivo_val = objetivo_map.get(datos.objetivo.lower(), Objetivo.RECOMPOSICION)
        nivel_val = nivel_map.get(datos.nivel.lower(), Nivel.PRINCIPIANTE)
        sexo_val = sexo_map.get(datos.sexo.lower(), Sexo.MASCULINO)
        equipo_val = equipo_map.get(datos.equipamiento.lower(), Equipamiento.GIMNASIO_COMPLETO)

        return Athlete(
            nombre=datos.nombre,
            objetivo=objetivo_val,
            nivel=nivel_val,
            sexo=sexo_val,
            edad=datos.edad,
            peso=datos.peso,
            talla=datos.talla,
            equipamiento=equipo_val,
            dias_semana=datos.dias_semana,
            lesiones=datos.lesiones,
            deporte_paralelo=datos.deporte_paralelo,
        )

    def _calcular_biometria(
        self,
        peso: float,
        talla: float,
        edad: int,
        sexo: str,
    ) -> Biometria:
        """Calcula biometría del atleta."""
        imc = calcular_imc(peso, talla)
        grasa = estimar_grasa(edad, sexo, imc)
        agua = estimar_agua(grasa)

        return Biometria(
            peso=peso,
            talla=talla,
            imc=imc,
            masa_muscular=round(100 - grasa - 5, 1),
            agua=agua,
            grasa_visceral=round(grasa * 0.15, 1),
        )

    def _nutrition_generar_gasto(self, nivel: str) -> GastoEnergetico:
        """Calcula gasto energético según nivel."""
        return calcular_gasto(nivel)


# Instancia singleton
_training_service: TrainingGeneratorService | None = None


def get_training_generator_service() -> TrainingGeneratorService:
    """Obtiene instancia singleton del servicio."""
    global _training_service
    if _training_service is None:
        _training_service = TrainingGeneratorService()
    return _training_service
