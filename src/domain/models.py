"""
Modelos de dominio usando Pydantic v2.
Valicación de frontera entre capas.
"""
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────
class Nivel(str, Enum):
    PRINCIPIANTE = "Principiante"
    INTERMEDIO = "Intermedio"
    AVANZADO = "Avanzado"


class Objetivo(str, Enum):
    QUEMAR_GRASA = "Quemar Grasa"
    GANAR_MUSCULO = "Ganar Músculo"
    RECOMPOSICION = "Recomposición Corporal"


class Sexo(str, Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"


class Equipamiento(str, Enum):
    GIMNASIO_COMPLETO = "Gimnasio completo"
    CASA_CON_MANCUERNAS = "Casa con mancuernas"
    PESO_CORPORAL = "Peso corporal"


class BloqueATR(str, Enum):
    ACUMULACION = "Acumulación"
    TRANSMUTACION = "Transmutación"
    REALIZACION = "Realización"


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────
class Athlete(BaseModel):
    """
    Datos del atleta. Modelo válido en frontera de aplicación.
    """
    model_config = {"str_strip_whitespace": True}

    nombre: str = Field(..., min_length=1, max_length=100)
    objetivo: Objetivo
    nivel: Nivel
    sexo: Sexo
    edad: int = Field(..., ge=10, le=100)
    peso: float = Field(..., ge=30, le=300)  # kg
    talla: float = Field(..., ge=100, le=250)  # cm
    equipamiento: Equipamiento
    dias_semana: int = Field(..., ge=2, le=5)
    lesiones: str = Field(default="Ninguna")
    deporte_paralelo: str = Field(default="Ninguno")

    @field_validator("lesiones", "deporte_paralelo")
    @classmethod
    def normalize_empty(cls, v: str) -> str:
        if not v or v.lower() in ("ninguno", "ninguna", "n/a", "-"):
            return "Ninguna"
        return v


class Biometria(BaseModel):
    """Resultados de biometría calculada."""
    peso: float
    talla: float
    imc: float
    masa_muscular: float
    agua: float
    grasa_visceral: float


class Macros(BaseModel):
    """Macronutrientes calculados."""
    prot_g: int
    carb_g: int
    gras_g: int
    prot_p: int  # porcentaje
    carb_p: int
    gras_p: int


class GastoEnergetico(BaseModel):
    """Desglose del gasto energético."""
    tmb: int  # porcentaje
    neat: int
    ejercicio: int
    tef: int


class ATRConfig(BaseModel):
    """Configuración de un bloque ATR."""
    bloque: BloqueATR
    rir: str
    series_base: int
    reps: str
    volumen: str
    intensidad: str
    es_deload: bool = False


class Ejercicio(BaseModel):
    """Ejercicio seleccionado para una sesión."""
    nombre: str
    patron: str
    objetivo_tecnico: str
    es_compuesto: bool
    series_reps: str = ""
    carga: str = ""


class SesionEntrenamiento(BaseModel):
    """Una sesión de entrenamiento."""
    dia: int
    nombre_sesion: str
    ejercicios: list[Ejercicio] = Field(default_factory=list)


class SemanaEntrenamiento(BaseModel):
    """Una semana de entrenamiento."""
    numero: int
    bloque: BloqueATR
    es_deload: bool = False
    sesiones: list[SesionEntrenamiento] = Field(default_factory=list)


class TrainingContext(BaseModel):
    """
    Contexto completo de entrenamiento para un atleta.
    Incluye todos los datos necesarios para generar programas.
    """
    athlete: Athlete
    biometria: Biometria
    macros: Macros
    gasto: GastoEnergetico
    semanas: list[SemanaEntrenamiento] = Field(default_factory=list)

    @property
    def semana_actual(self) -> int | None:
        """Última semana configurada."""
        if self.semanas:
            return max(s.numero for s in self.semanas)
        return None


class NutricionPlan(BaseModel):
    """Plan nutricional completo."""
    estrategia_principal: str
    proteinas: str
    carbohidratos: str
    grasas: str
    guia_compras: list[dict] = Field(default_factory=list)
    reglas_oro: list[str] = Field(default_factory=list)


class ProgramaCompleto(BaseModel):
    """
    Programa completo generado para un atleta.
    No serializa metadatos internos (_meta).
    """
    model_config = {"populate_by_name": True}

    athlete: Athlete
    biometria: Biometria
    macros: Macros
    gasto: GastoEnergetico
    nutricion: NutricionPlan
    semanas: list[SemanaEntrenamiento] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict, repr=False)
