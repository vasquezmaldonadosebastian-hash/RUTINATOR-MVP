"""
Repositorio de ejercicios con caché y métodos de filtrado puros.
Reemplaza el DF_EJERCICIOS global del monolito.
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Ruta del CSV de ejercicios
_CSV_PATH = Path(__file__).parent.parent.parent.parent / "data" / "ejercicios.csv"


class ExerciseRepository:
    """
    Repositorio de ejercicios con carga única y caché en memoria.

    Provee métodos de filtrado puros sin efectos secundarios.
    Thread-safe para uso en thread pool.
    """

    def __init__(self, csv_path: Path | None = None) -> None:
        """
        Inicializa el repositorio.

        Args:
            csv_path: Ruta opcional al CSV de ejercicios.
        """
        self._csv_path = csv_path or _CSV_PATH
        self._df: pd.DataFrame | None = None
        self._loaded = False

    def _load_df(self) -> pd.DataFrame:
        """Carga y normaliza el CSV. Thread-safe."""
        if self._loaded and self._df is not None:
            return self._df

        try:
            df = pd.read_csv(self._csv_path, dtype=str).fillna("")
            df.columns = df.columns.str.strip()
            df["Es_Compuesto"] = df["Es_Compuesto"].str.strip().eq("1")

            self._df = df
            self._loaded = True
            logger.info(f"Ejercicios cargados: {len(df)} registros")
            return df
        except FileNotFoundError:
            logger.error(f"CSV no encontrado: {self._csv_path}")
            raise RuntimeError(f"No se encontró el CSV en: {self._csv_path}") from None

    @property
    def dataframe(self) -> pd.DataFrame:
        """Acceso al DataFrame completo."""
        return self._load_df()

    # ─────────────────────────────────────────────
    # FILTROS PUROS
    # ─────────────────────────────────────────────

    def filtrar_por_equipamiento(
        self,
        equipamiento: str,
    ) -> pd.DataFrame:
        """
        Filtra ejercicios por tipo de equipamiento.

        Args:
            equipamiento: Descripción del equipamiento disponible.

        Returns:
            DataFrame filtrado.
        """
        df = self.dataframe
        eq_lower = equipamiento.lower()

        # Si es entrenamiento en casa sin máquinas
        sin_maquinas = any(
            w in eq_lower
            for w in ["casa", "sin", "cuerpo", "bodyweight", "peso corporal"]
        )

        if sin_maquinas:
            return df[df["Equipamiento"].isin(["Peso Corporal", "Mancuerna"])]

        return df.copy()

    def filtrar_por_lesiones(self, lesiones: str) -> pd.DataFrame:
        """
        Aplica filtros de seguridad según lesiones del atleta.

        Args:
            lesiones: Descripción de lesiones del atleta.

        Returns:
            DataFrame filtrado.
        """
        df = self.dataframe.copy()
        lesiones_lower = lesiones.lower()

        # Filtrar ejercicios a evitar según lesión
        if any(w in lesiones_lower for w in ["lumbar", "espalda", "hernia", "disco"]):
            df = df[df["Flag_Lesion"] != "Evitar_Lumbar"]

        if any(w in lesiones_lower for w in ["rodilla", "menisco", "ligamento"]):
            df = df[df["Flag_Lesion"] != "Evitar_Rodilla"]

        if any(w in lesiones_lower for w in ["hombro", "manguito", "rotador"]):
            df = df[df["Flag_Lesion"] != "Evitar_Hombro"]

        return df

    def filtrar_completo(
        self,
        equipamiento: str,
        lesiones: str = "Ninguna",
    ) -> pd.DataFrame:
        """
        Aplica todos los filtros de seguridad y equipamiento.

        Args:
            equipamiento: Equipamiento disponible.
            lesiones: Lesiones del atleta.

        Returns:
            DataFrame filtrado listo para selección.
        """
        df = self.filtrar_por_equipamiento(equipamiento)
        df = self.filtrar_por_lesiones(lesiones)
        return df.reset_index(drop=True)

    # ─────────────────────────────────────────────
    # SELECCIÓN DE EJERCICIOS
    # ─────────────────────────────────────────────

    def seleccionar_por_patron(
        self,
        df: pd.DataFrame,
        patron: str,
        nivel: str = "Principiante",
        variante: int = 0,
    ) -> dict | None:
        """
        Selecciona un ejercicio para un patrón de movimiento dado.

        Args:
            df: DataFrame filtrado.
            patron: Patrón de movimiento (ej: "Sentadilla", "Empuje_Horizontal").
            nivel: Nivel del atleta.
            variante: Índice para variabilidad (0 o 1).

        Returns:
            Dict con datos del ejercicio o None si no hay candidatos.
        """
        candidatos = df[df["Patron"] == patron].copy()
        if candidatos.empty:
            logger.warning(f"No hay ejercicios para patrón: {patron}")
            return None

        # Prioridad por nivel
        niveles_fallback = [nivel, "Principiante", "Intermedio", "Avanzado"]
        for lvl in niveles_fallback:
            subset = candidatos[candidatos["Nivel"] == lvl]
            if not subset.empty:
                candidatos = subset
                break

        # Priorizar compuestos para patrones principales
        if patron != "Core":
            compuestos = candidatos[candidatos["Es_Compuesto"]]
            if not compuestos.empty:
                candidatos = compuestos

        # Variabilidad por variante
        idx = variante % len(candidatos)
        fila = candidatos.iloc[idx]

        return {
            "nombre": fila["Nombre_ES"],
            "patron": patron,
            "objetivo_tecnico": fila["Objetivo_Tecnico"],
            "es_compuesto": bool(fila["Es_Compuesto"]),
        }

    def seleccionar_ejercicios_sesion(
        self,
        df: pd.DataFrame,
        patrones: list[str],
        nivel: str = "Principiante",
        variante: int = 0,
    ) -> list[dict]:
        """
        Selecciona ejercicios para una sesión completa.

        Args:
            df: DataFrame filtrado.
            patrones: Lista de patrones de movimiento requeridos.
            nivel: Nivel del atleta.
            variante: Índice de variabilidad.

        Returns:
            Lista de ejercicios seleccionados.
        """
        seleccionados = []
        for patron in patrones:
            ejercicio = self.seleccionar_por_patron(df, patron, nivel, variante)
            if ejercicio:
                seleccionados.append(ejercicio)

        return seleccionados


# ─────────────────────────────────────────────
# INSTANCIA SINGLETON
# ─────────────────────────────────────────────
_exercise_repo: ExerciseRepository | None = None


def get_exercise_repository() -> ExerciseRepository:
    """
    Obtiene la instancia singleton del repositorio.

    Returns:
        Instancia de ExerciseRepository.
    """
    global _exercise_repo
    if _exercise_repo is None:
        _exercise_repo = ExerciseRepository()
        logger.info("ExerciseRepository inicializado")
    return _exercise_repo


def reset_repository() -> None:
    """Reinicia el repositorio (para testing)."""
    global _exercise_repo
    _exercise_repo = None
