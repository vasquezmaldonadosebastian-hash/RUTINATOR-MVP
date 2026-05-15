"""
Reglas de negocio puras - Sin I/O, sin dependencias externas.
Cálculos fisiológicos y lógica ATR.
"""
from src.domain.models import (
    ATRConfig,
    BloqueATR,
    GastoEnergetico,
    Macros,
    NutricionPlan,
)

# ════════════════════════════════════════════
# CONSTANTES ATR
# ════════════════════════════════════════════
SEMANAS_DELOAD: set[int] = {4, 8, 12}

ATR_CONFIGS: dict[BloqueATR, ATRConfig] = {
    BloqueATR.ACUMULACION: ATRConfig(
        bloque=BloqueATR.ACUMULACION,
        rir="RIR 3",
        series_base=4,
        reps="10-12",
        volumen="Alto",
        intensidad="Media",
    ),
    BloqueATR.TRANSMUTACION: ATRConfig(
        bloque=BloqueATR.TRANSMUTACION,
        rir="RIR 2",
        series_base=3,
        reps="8-10",
        volumen="Medio",
        intensidad="Alta",
    ),
    BloqueATR.REALIZACION: ATRConfig(
        bloque=BloqueATR.REALIZACION,
        rir="RIR 1",
        series_base=2,
        reps="6-8",
        volumen="Bajo",
        intensidad="Máxima",
    ),
}

# ════════════════════════════════════════════
# SPLITS DE ENTRENAMIENTO
# ════════════════════════════════════════════
SPLITS: dict[int, list[str]] = {
    2: ["Full Body A", "Full Body B"],
    3: ["Full Body A", "Full Body B", "Full Body C"],
    4: ["Torso", "Pierna", "Torso", "Pierna"],
    5: ["Empuje", "Tracción", "Pierna", "Torso", "Pierna"],
}

PATRONES_POR_SESION: dict[str, list[str]] = {
    "Full Body A": ["Sentadilla", "Empuje_Horizontal", "Tracción_Horizontal", "Core", "Unilateral"],
    "Full Body B": ["Bisagra_Cadera", "Empuje_Vertical", "Tracción_Vertical", "Core", "Unilateral"],
    "Full Body C": ["Sentadilla", "Empuje_Horizontal", "Tracción_Vertical", "Core", "Bisagra_Cadera"],
    "Torso": ["Empuje_Horizontal", "Empuje_Vertical", "Tracción_Horizontal", "Tracción_Vertical", "Core"],
    "Pierna": ["Sentadilla", "Bisagra_Cadera", "Unilateral", "Core"],
    "Empuje": ["Empuje_Horizontal", "Empuje_Vertical", "Core"],
    "Tracción": ["Tracción_Horizontal", "Tracción_Vertical", "Core"],
}


# ════════════════════════════════════════════
# REGLAS FISIOLÓGICAS PURAS
# ════════════════════════════════════════════
def calcular_imc(peso_kg: float, altura_cm: float) -> float:
    """
    Calcula el Índice de Masa Corporal.

    Args:
        peso_kg: Peso en kilogramos
        altura_cm: Altura en centímetros

    Returns:
        IMC redondeado a 1 decimal
    """
    if peso_kg <= 0 or altura_cm <= 0:
        return 0.0
    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m**2)
    return round(imc, 1)


def estimar_grasa(edad: int, sexo: str, imc: float) -> float:
    """
    Estima porcentaje de grasa corporal usando fórmula de Deurenberg.

    Args:
        edad: Edad en años
        sexo: "Masculino" o "Femenino"
        imc: Índice de masa corporal

    Returns:
        Porcentaje de grasa (5-50%)
    """
    sexo_val = 1 if sexo == "Masculino" else 0
    grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * sexo_val) - 5.4
    return round(max(5.0, min(grasa, 50.0)), 1)


def estimar_agua(grasa: float) -> float:
    """
    Estima porcentaje de agua corporal.

    Args:
        grasa: Porcentaje de grasa corporal

    Returns:
        Porcentaje de agua
    """
    return round(100 - grasa - 40, 1)


def calcular_macros(objetivo: str, peso_kg: float) -> Macros:
    """
    Calcula macronutrientes según objetivo.

    Args:
        objetivo: Objetivo del entrenamiento
        peso_kg: Peso del atleta en kg

    Returns:
        Macros con gramos y porcentajes
    """
    objetivo_lower = objetivo.lower()

    if "grasa" in objetivo_lower or "quemar" in objetivo_lower:
        prot_g = round(peso_kg * 2.2)
        gras_g = round(peso_kg * 0.9)
        carb_g = round(peso_kg * 2.0)
        prot_p, carb_p, gras_p = 35, 40, 25
    elif "músculo" in objetivo_lower or "ganar" in objetivo_lower or "hipertrofia" in objetivo_lower:
        prot_g = round(peso_kg * 2.0)
        gras_g = round(peso_kg * 1.0)
        carb_g = round(peso_kg * 3.5)
        prot_p, carb_p, gras_p = 30, 45, 25
    else:  # recomposición
        prot_g = round(peso_kg * 2.1)
        gras_g = round(peso_kg * 1.0)
        carb_g = round(peso_kg * 2.5)
        prot_p, carb_p, gras_p = 33, 42, 25

    return Macros(
        prot_g=prot_g,
        carb_g=carb_g,
        gras_g=gras_g,
        prot_p=prot_p,
        carb_p=carb_p,
        gras_p=gras_p,
    )


def calcular_gasto(nivel: str) -> GastoEnergetico:
    """
    Calcula desglose del gasto energético según nivel.

    Args:
        nivel: Nivel de experiencia (Principiante/Intermedio/Avanzado)

    Returns:
        GastoEnergetico con porcentajes
    """
    if nivel == "Principiante":
        return GastoEnergetico(tmb=65, neat=18, ejercicio=8, tef=9)
    elif nivel == "Intermedio":
        return GastoEnergetico(tmb=60, neat=20, ejercicio=11, tef=9)
    else:  # Avanzado
        return GastoEnergetico(tmb=55, neat=22, ejercicio=14, tef=9)


# ════════════════════════════════════════════
# REGLAS ATR PURAS
# ════════════════════════════════════════════
def obtener_bloque_desde_semana(semana: int) -> BloqueATR:
    """Obtiene el bloque ATR para una semana dada."""
    if 1 <= semana <= 4:
        return BloqueATR.ACUMULACION
    elif 5 <= semana <= 8:
        return BloqueATR.TRANSMUTACION
    else:
        return BloqueATR.REALIZACION


def es_semana_deload(semana: int) -> bool:
    """Determina si una semana es de deload."""
    return semana in SEMANAS_DELOAD


def obtener_config_semana(semana: int) -> ATRConfig:
    """
    Obtiene configuración ATR para una semana específica.
    Aplica deload automático en semanas 4, 8, 12.
    """
    bloque = obtener_bloque_desde_semana(semana)
    config = ATR_CONFIGS[bloque].model_copy()

    if es_semana_deload(semana):
        config.es_deload = True
        config.rir = "RIR 4 (DELOAD)"
        config.reps = "12-15"
        config.series_base = max(2, int(config.series_base * 0.7))

    return config


def obtener_titulo_semana(semana: int) -> str:
    """Genera etiqueta para la semana."""
    bloque = obtener_bloque_desde_semana(semana)
    deload = " ⚡ DELOAD" if es_semana_deload(semana) else ""

    if bloque == BloqueATR.ACUMULACION:
        titulo = "Acumulación (Volumen Alto)"
    elif bloque == BloqueATR.TRANSMUTACION:
        titulo = "Transmutación (Intensidad Alta)"
    else:
        titulo = "Realización (Intensidad Máxima)"

    return f"Semana {semana} - {titulo}{deload}"


def obtener_split(dias: int) -> list[str]:
    """Obtiene la distribución de sesiones según días disponibles."""
    return SPLITS.get(dias, SPLITS[3])


def obtener_patrones_sesion(nombre_sesion: str) -> list[str]:
    """Obtiene patrones de movimiento para una sesión."""
    return PATRONES_POR_SESION.get(nombre_sesion, [])


def obtener_mes_desde_semana(semana: int) -> int:
    """Convierte semana (1-12) a mes (1-3)."""
    if 1 <= semana <= 4:
        return 1
    elif 5 <= semana <= 8:
        return 2
    return 3


# ════════════════════════════════════════════
# NUTRICIÓN
# ════════════════════════════════════════════
def generar_estrategia_nutricional(objetivo: str, macros: Macros) -> NutricionPlan:
    """
    Genera estrategia nutricional según objetivo.

    Args:
        objetivo: Objetivo del entrenamiento
        macros: Macros calculados

    Returns:
        NutricionPlan con estrategia y recomendaciones
    """
    objetivo_lower = objetivo.lower()

    if "grasa" in objetivo_lower or "quemar" in objetivo_lower:
        principal = (
            "Tu estrategia nutricional se basa en un déficit calórico moderado "
            "(-300 a -400 kcal/día) con alta ingesta proteica para preservar "
            "masa muscular mientras pierdes grasa. Prioriza alimentos de alta "
            "saciedad y bajo índice glucémico."
        )
        guia = [
            {"categoría": "Proteína animal", "alimentos": "Pollo, pavo, huevos, atún, salmón", "frecuencia": "Diaria"},
            {"categoría": "Verduras", "alimentos": "Espinaca, brócoli, zucchini, tomate", "frecuencia": "Abundante"},
            {"categoría": "Frutas bajas azúcar", "alimentos": "Manzana verde, bayas, pomelo", "frecuencia": "1-2/día"},
        ]
    elif "músculo" in objetivo_lower or "ganar" in objetivo_lower:
        principal = (
            "Tu estrategia nutricional se basa en un superávit calórico limpio "
            "(+200 a +300 kcal/día). Alta ingesta de proteína para síntesis "
            "muscular y carbohidratos periworkout para maximizar el rendimiento."
        )
        guia = [
            {"categoría": "Carbohidratos", "alimentos": "Avena, arroz integral, papa, camote, quinoa", "frecuencia": "Diaria"},
            {"categoría": "Proteína", "alimentos": "Pollo, Carne, Huevos, Proteína whey", "frecuencia": "Diaria"},
            {"categoría": "Frutas", "alimentos": "Plátano, mango, naranja", "frecuencia": "2-3/día"},
        ]
    else:  # recomposición
        principal = (
            "Tu estrategia de recomposición corporal requiere comer cerca de tu "
            "mantenimiento calórico, con alta proteína para construir músculo y "
            "perder grasa simultáneamente."
        )
        guia = [
            {"categoría": "Proteína", "alimentos": "Pollo, pescado, huevos, legumbres", "frecuencia": "Diaria"},
            {"categoría": "Verduras", "alimentos": "Variedad de colores", "frecuencia": "Abundante"},
            {"categoría": "Carbohidratos", "alimentos": "Arroz integral, avena, frutas", "frecuencia": "Diaria"},
        ]

    reglas = [
        "Come proteína en cada comida principal.",
        "Carbohidratos complejos antes y después del entrenamiento.",
        "No elimines grupos alimentarios: ajusta porciones.",
        "Prepara comidas con anticipación (meal prep dominical).",
        "Duerme 7-9 horas: el músculo se construye en el descanso.",
    ]

    return NutricionPlan(
        estrategia_principal=principal,
        proteinas=f"{macros.prot_g}g/día",
        carbohidratos=f"{macros.carb_g}g/día",
        grasas=f"{macros.gras_g}g/día",
        guia_compras=guia,
        reglas_oro=reglas,
    )


def generar_intro_neat(objetivo: str) -> str:
    """Genera introducción personalizada sobre NEAT."""
    return (
        f"El NEAT (Non-Exercise Activity Thermogenesis) representa toda la energía "
        f"que gastas fuera del entrenamiento programado. Para tu objetivo de "
        f"{objetivo.lower()}, optimizar el NEAT puede representar 200-400 kcal "
        f"adicionales al día sin esfuerzo percibido."
    )


def generar_estrategias_neat() -> list[str]:
    """Genera lista de estrategias NEAT."""
    return [
        "Caminata diaria: 8.000-10.000 pasos mínimos.",
        "Escaleras siempre: Evita ascensores en menos de 4 pisos.",
        "Descansos activos: Cada 45 min sedentario, 5 min de movimiento.",
        "Reuniones caminando: Reemplaza reuniones sentadas por caminatas.",
        "Tareas domésticas: Limpiar, cocinar y ordenar suman más de lo que crees.",
    ]
