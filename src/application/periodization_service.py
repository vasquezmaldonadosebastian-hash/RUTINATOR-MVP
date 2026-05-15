"""
Servicio de periodización ATR y generación de programas de entrenamiento.
Orquesta el repositorio de ejercicios y las reglas de dominio.
"""
import logging
from dataclasses import dataclass

from src.domain.models import (
    ATRConfig,
    BloqueATR,
    Ejercicio,
    SemanaEntrenamiento,
    SesionEntrenamiento,
)
from src.domain.rules import (
    es_semana_deload,
    obtener_bloque_desde_semana,
    obtener_config_semana,
    obtener_patrones_sesion,
    obtener_split,
)
from src.infrastructure.repositories import get_exercise_repository

logger = logging.getLogger(__name__)


@dataclass
class PeriodizationResult:
    """Resultado de la generación de periodización."""
    semanas: list[SemanaEntrenamiento]
    es_deload: bool


class PeriodizationService:
    """
    Servicio de periodización ATR.

    Maneja la generación de programas de entrenamiento siguiendo
    el modelo ATR (Acumulación, Transmutación, Realización) con
    anti-monotonía y deloads automáticos.
    """

    def __init__(self) -> None:
        self._repo = get_exercise_repository()

    def generar_programa(
        self,
        nivel: str,
        objetivo: str,
        lesiones: str,
        equipamiento: str,
        dias_semana: int,
        semana: int | None = None,
    ) -> list[SemanaEntrenamiento]:
        """
        Genera programa de entrenamiento para 12 semanas o semana específica.

        Args:
            nivel: Nivel del atleta (Principiante/Intermedio/Avanzado)
            objetivo: Objetivo del entrenamiento
            lesiones: Lesiones del atleta
            equipamiento: Equipamiento disponible
            dias_semana: Días de entrenamiento por semana
            semana: Semana específica a generar (None = todas las semanas)

        Returns:
            Lista de semanas de entrenamiento
        """
        # Filtrar ejercicios según restricciones
        df_filtrado = self._repo.filtrar_completo(equipamiento, lesiones)

        # Determinar semanas a generar
        if semana is not None and 1 <= semana <= 12:
            semanas_a_generar = [semana]
        else:
            semanas_a_generar = list(range(1, 13))

        # Obtener split según días
        split = obtener_split(dias_semana)

        semanas = []
        historial_ejercicios: dict[str, list[dict]] = {}

        for semana_actual in semanas_a_generar:
            bloque = obtener_bloque_desde_semana(semana_actual)
            es_deload = es_semana_deload(semana_actual)

            sesiones = self._generar_semana(
                df_filtrado,
                split,
                nivel,
                semana_actual,
                bloque,
                historial_ejercicios,
            )

            semana_entrenamiento = SemanaEntrenamiento(
                numero=semana_actual,
                bloque=bloque,
                es_deload=es_deload,
                sesiones=sesiones,
            )
            semanas.append(semana_entrenamiento)

            # Actualizar historial para anti-monotonía
            self._actualizar_historial(
                historial_ejercicios,
                bloque.value,
                sesiones,
            )

        logger.info(f"Programa generado: {len(semanas)} semanas")
        return semanas

    def _generar_semana(
        self,
        df_filtrado,
        split: list[str],
        nivel: str,
        semana: int,
        bloque: BloqueATR,
        historial: dict[str, list[dict]],
    ) -> list[SesionEntrenamiento]:
        """Genera los ejercicios para una semana completa."""
        sesiones = []

        for dia_idx, nombre_sesion in enumerate(split):
            patrones = obtener_patrones_sesion(nombre_sesion)
            variante = dia_idx % 2  # Alternar para variabilidad

            # Seleccionar ejercicios
            ejercicios_raw = self._repo.seleccionar_ejercicios_sesion(
                df_filtrado, patrones, nivel, variante
            )

            # Aplicar configuración ATR
            config = obtener_config_semana(semana)

            # Aplicar anti-monotonía si hay cambio de bloque
            ejercicios_periodizados = self._aplicar_anti_monotonia(
                ejercicios_raw, semana, bloque, historial
            )

            # Crear objetos Ejercicio
            ejercicios = [
                Ejercicio(
                    nombre=ej["nombre"],
                    patron=ej["patron"],
                    objetivo_tecnico=ej["objetivo_tecnico"],
                    es_compuesto=ej["es_compuesto"],
                    series_reps=self._format_series_reps(config),
                    carga=config.rir,
                )
                for ej in ejercicios_periodizados
            ]

            sesiones.append(SesionEntrenamiento(
                dia=dia_idx + 1,
                nombre_sesion=nombre_sesion,
                ejercicios=ejercicios,
            ))

        return sesiones

    def _aplicar_anti_monotonia(
        self,
        ejercicios: list[dict],
        semana: int,
        bloque_actual: BloqueATR,
        historial: dict[str, list[dict]],
    ) -> list[dict]:
        """
        Aplica lógica anti-monotonía.

        Al cambiar de bloque, los ejercicios accesorios rotan
        mientras los compuestos se mantienen.
        """
        if semana <= 1:
            return ejercicios

        # Obtener bloque anterior
        bloque_anterior = None
        if 5 <= semana <= 8:
            bloque_anterior = BloqueATR.ACUMULACION.value
        elif 9 <= semana <= 12:
            bloque_anterior = BloqueATR.TRANSMUTACION.value

        if not bloque_anterior or bloque_anterior not in historial:
            return ejercicios

        ejercicios_bloque_anterior = historial[bloque_anterior]

        resultado = []
        for ej in ejercicios:
            # Si es compuesto, mantener
            if ej.get("es_compuesto", False):
                resultado.append(ej)
                continue

            # Si es accesorio, buscar alternativa
            patron = ej.get("patron", "")
            mismos_patron = [
                e for e in ejercicios_bloque_anterior
                if e.get("patron", "") == patron and not e.get("es_compuesto", False)
            ]

            if len(mismos_patron) > 1:
                # Rotar a otro ejercicio
                idx_actual = next(
                    (i for i, e in enumerate(mismos_patron)
                     if e.get("nombre") == ej.get("nombre")),
                    -1
                )
                siguiente_idx = (idx_actual + 1) % len(mismos_patron)
                resultado.append(mismos_patron[siguiente_idx])
            else:
                resultado.append(ej)

        return resultado

    def _actualizar_historial(
        self,
        historial: dict[str, list[dict]],
        bloque: str,
        sesiones: list[SesionEntrenamiento],
    ) -> None:
        """Actualiza el historial de ejercicios por bloque (guarda todos los campos)."""
        ejercicios_bloque = []
        for sesion in sesiones:
            for ej in sesion.ejercicios:
                ejercicios_bloque.append({
                    "nombre": ej.nombre,
                    "patron": ej.patron,
                    "objetivo_tecnico": ej.objetivo_tecnico,
                    "es_compuesto": ej.es_compuesto,
                })
        historial[bloque] = ejercicios_bloque

    def _format_series_reps(self, config: ATRConfig) -> str:
        """Formatea series × reps según configuración."""
        if config.es_deload:
            return f"{config.series_base} x {config.reps}"
        return f"{config.series_base} x {config.reps}"


# Instancia singleton
_periodization_service: PeriodizationService | None = None


def get_periodization_service() -> PeriodizationService:
    """Obtiene instancia singleton del servicio."""
    global _periodization_service
    if _periodization_service is None:
        _periodization_service = PeriodizationService()
    return _periodization_service
