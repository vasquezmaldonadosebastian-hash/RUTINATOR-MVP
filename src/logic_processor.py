import io
import math
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# ─────────────────────────────────────────────
# CARGA DEL DATAFRAME (singleton al importar)
# ─────────────────────────────────────────────
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ejercicios.csv")

def _cargar_df() -> pd.DataFrame:
    """Carga y normaliza el CSV de ejercicios. Falla con mensaje claro si no existe."""
    try:
        df = pd.read_csv(_CSV_PATH, dtype=str).fillna("")
        df.columns = df.columns.str.strip()
        df["Es_Compuesto"] = df["Es_Compuesto"].str.strip().eq("1")
        return df
    except FileNotFoundError:
        raise RuntimeError(f"No se encontró el CSV de ejercicios en: {_CSV_PATH}")

# DataFrame global — se carga una sola vez al importar el módulo
DF_EJERCICIOS: pd.DataFrame = _cargar_df()

# ─────────────────────────────────────────────
# PALETA DE COLORES
# ─────────────────────────────────────────────
C_PRIMARIO    = colors.HexColor("#0F172A")
C_SECUNDARIO  = colors.HexColor("#2563EB")
C_ACENTO      = colors.HexColor("#10B981")
C_TEXTO       = colors.HexColor("#334155")
C_FONDO_CLARO = colors.HexColor("#E2E8F0")
C_BLANCO      = colors.white
C_ROJO        = colors.HexColor("#E11D48")
C_AMARILLO    = colors.HexColor("#F59E0B")

# ─────────────────────────────────────────────
# SYSTEM PROMPT DEL COACH (referencia interna)
# ─────────────────────────────────────────────
COACH_SYSTEM_PROMPT = """
Eres un entrenador profesional especializado en fuerza, hipertrofia, recomposición corporal,
pérdida de grasa, acondicionamiento físico y entrenamiento para principiantes e intermedios.
Actúas como un entrenador real: personalizas cada plan según edad, sexo, peso, altura,
experiencia, lesiones, disponibilidad, equipamiento y objetivo.
NUNCA inventas pesos. NUNCA generas rutinas genéricas.
Planes de 12 semanas: Mes 1 Adaptación, Mes 2 Volumen, Mes 3 Intensificación.
Incluyes siempre: empuje/tracción horizontal y vertical, dominante rodilla/cadera, core,
unilateral y movilidad.
"""

# ─────────────────────────────────────────────
# HELPERS DE CÁLCULO
# ─────────────────────────────────────────────
def calcular_imc(peso_kg: float, altura_cm: float) -> float:
    try:
        return round(peso_kg / ((altura_cm / 100) ** 2), 1)
    except Exception:
        return 0.0

def estimar_grasa(edad: int, sexo: str, imc: float) -> float:
    """Fórmula de Deurenberg simplificada."""
    sexo_val = 1 if sexo == "Masculino" else 0
    grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * sexo_val) - 5.4
    return round(max(5.0, min(grasa, 50.0)), 1)

def estimar_agua(grasa: float) -> float:
    return round(100 - grasa - 40, 1)

def calcular_macros(objetivo: str, peso_kg: float) -> dict:
    """Retorna gramos y porcentajes de macros según objetivo."""
    if "grasa" in objetivo.lower() or "quemar" in objetivo.lower():
        prot_g = round(peso_kg * 2.2)
        gras_g = round(peso_kg * 0.9)
        carb_g = round(peso_kg * 2.0)
        prot_p, carb_p, gras_p = 35, 40, 25
    elif "músculo" in objetivo.lower() or "ganar" in objetivo.lower() or "hipertrofia" in objetivo.lower():
        prot_g = round(peso_kg * 2.0)
        gras_g = round(peso_kg * 1.0)
        carb_g = round(peso_kg * 3.5)
        prot_p, carb_p, gras_p = 30, 45, 25
    else:  # recomposición
        prot_g = round(peso_kg * 2.1)
        gras_g = round(peso_kg * 1.0)
        carb_g = round(peso_kg * 2.5)
        prot_p, carb_p, gras_p = 33, 42, 25
    return {
        "prot_g": prot_g, "carb_g": carb_g, "gras_g": gras_g,
        "prot_p": prot_p, "carb_p": carb_p, "gras_p": gras_p
    }

def calcular_gasto(nivel: str, objetivo: str) -> dict:
    """Porcentajes de gasto energético según nivel de actividad."""
    if nivel == "Principiante":
        return {"tmb": 65, "neat": 18, "ejercicio": 8, "tef": 9}
    elif nivel == "Intermedio":
        return {"tmb": 60, "neat": 20, "ejercicio": 11, "tef": 9}
    else:
        return {"tmb": 55, "neat": 22, "ejercicio": 14, "tef": 9}

# ─────────────────────────────────────────────
# GENERADOR DE PROGRAMA (8 TABLAS)
# ─────────────────────────────────────────────
def construir_programa(d: dict) -> dict:
    """
    Recibe el dict de datos del usuario y devuelve las 8 tablas
    como listas de dicts listos para renderizar en PDF.
    """
    nombre   = d.get("atleta", "Atleta")
    objetivo = d.get("objetivo", "Recomposición")
    nivel    = d.get("nivel", "Principiante")
    sexo     = d.get("sexo", "Masculino")
    edad     = int(d.get("edad", 25))
    peso     = float(str(d.get("peso", 70)).replace(",", "."))
    talla    = float(str(d.get("talla", 170)).replace(",", "."))
    lesiones = d.get("lesiones", "Ninguna")
    equipo   = d.get("equipamiento", "Gimnasio completo")
    dias     = d.get("dias_semana", "3")
    deporte  = d.get("deporte_paralelo", "Ninguno")

    imc    = calcular_imc(peso, talla)
    grasa  = estimar_grasa(edad, sexo, imc)
    agua   = estimar_agua(grasa)
    macros = calcular_macros(objetivo, peso)
    gasto  = calcular_gasto(nivel, objetivo)

    # ── Tabla 1: Atleta ──
    titulo_plan = f"Plan Trimestral · {objetivo} · {nivel}"
    intro = (
        f"Hola {nombre}, este es tu programa de 12 semanas diseñado específicamente "
        f"para tu objetivo de {objetivo.lower()}. Trabajaremos en tres fases progresivas: "
        f"adaptación anatómica, volumen y finalmente intensificación. "
        f"Cada semana tiene un propósito claro. Confía en el proceso."
    )
    tabla_atleta = [
        {"Campo": "Titulo",       "Valor": titulo_plan},
        {"Campo": "Atleta",       "Valor": nombre},
        {"Campo": "Objetivo",     "Valor": objetivo},
        {"Campo": "Introduccion", "Valor": intro},
    ]

    # ── Tabla 2: Biometría ──
    tabla_bio = [
        {"Indicador": "Peso (kg)",         "Valor": peso},
        {"Indicador": "Altura (cm)",        "Valor": talla},
        {"Indicador": "IMC",                "Valor": imc},
        {"Indicador": "% Masa Muscular",    "Valor": round(100 - grasa - 5, 1)},
        {"Indicador": "% Agua",             "Valor": agua},
        {"Indicador": "% Grasa Visceral",   "Valor": round(grasa * 0.15, 1)},
    ]

    # ── Tabla 3: Entrenamiento ──
    tabla_entrenamiento = _construir_entrenamiento(nivel, objetivo, lesiones, equipo, dias)

    # ── Tabla 4: Nutrición Texto ──
    texto_nut = _texto_nutricion(objetivo, peso, macros)
    tabla_nut_texto = [
        {"Campo": "Texto_Principal", "Valor": texto_nut["principal"]},
        {"Campo": "Proteinas",       "Valor": texto_nut["proteinas"]},
        {"Campo": "Carbohidratos",   "Valor": texto_nut["carbohidratos"]},
        {"Campo": "Grasas",          "Valor": texto_nut["grasas"]},
    ]

    # ── Tabla 5: Macros ──
    tabla_macros = [
        {"Macro": "Proteínas",     "Porcentaje": macros["prot_p"], "Color": "#E11D48"},
        {"Macro": "Carbohidratos", "Porcentaje": macros["carb_p"], "Color": "#2563EB"},
        {"Macro": "Grasas",        "Porcentaje": macros["gras_p"], "Color": "#F59E0B"},
    ]

    # ── Tabla 6: NEAT Texto ──
    neat_intro = (
        f"El NEAT (Non-Exercise Activity Thermogenesis) representa toda la energía que gastas "
        f"fuera del ejercicio programado: caminar, subir escaleras, moverte en casa. "
        f"Para tu objetivo de {objetivo.lower()}, optimizar el NEAT puede representar "
        f"entre 200-400 kcal adicionales al día sin esfuerzo percibido."
    )
    tabla_neat_texto = [{"Campo": "Introduccion", "Valor": neat_intro}]

    # ── Tabla 7: NEAT Estrategias ──
    tabla_neat_estrategias = [
        {"Estrategia": "Caminata diaria: 8.000-10.000 pasos mínimos. Usa el móvil como podómetro."},
        {"Estrategia": "Escaleras siempre: Evita ascensores en desplazamientos de menos de 4 pisos."},
        {"Estrategia": "Descansos activos: Cada 45 min de trabajo sedentario, 5 min de movimiento."},
        {"Estrategia": "Reuniones caminando: Reemplaza reuniones sentadas por caminatas cuando sea posible."},
        {"Estrategia": "Tareas domésticas: Limpiar, cocinar y ordenar suman más de lo que crees."},
    ]

    # ── Tabla 8: Gasto Energético ──
    tabla_gasto = [
        {"Componente": "TMB",      "Porcentaje": gasto["tmb"],      "Color": "#0F172A"},
        {"Componente": "NEAT",     "Porcentaje": gasto["neat"],     "Color": "#2563EB"},
        {"Componente": "Ejercicio","Porcentaje": gasto["ejercicio"],"Color": "#10B981"},
        {"Componente": "TEF",      "Porcentaje": gasto["tef"],      "Color": "#F59E0B"},
    ]

    return {
        "atleta":           tabla_atleta,
        "biometria":        tabla_bio,
        "entrenamiento":    tabla_entrenamiento,
        "nutricion_texto":  tabla_nut_texto,
        "macros":           tabla_macros,
        "neat_texto":       tabla_neat_texto,
        "neat_estrategias": tabla_neat_estrategias,
        "gasto_energetico": tabla_gasto,
        "_meta": {
            "nombre": nombre, "objetivo": objetivo, "nivel": nivel,
            "macros": macros, "gasto": gasto, "imc": imc, "grasa": grasa
        }
    }

# ─────────────────────────────────────────────
# MOTOR DE PERIODIZACIÓN — MACROCICLO / MESOCICLO / MICROCICLO
# ─────────────────────────────────────────────

# Mapeo de splits según días disponibles por semana
_SPLITS: dict = {
    "2": ["Full Body A", "Full Body B"],
    "3": ["Full Body A", "Full Body B", "Full Body C"],
    "4": ["Torso", "Pierna", "Torso", "Pierna"],
    "5": ["Empuje", "Tracción", "Pierna", "Torso", "Pierna"],
}

# Patrones de movimiento requeridos por tipo de sesión
_PATRONES_SESION: dict = {
    "Full Body A": ["Sentadilla", "Empuje_Horizontal", "Tracción_Horizontal", "Core", "Unilateral"],
    "Full Body B": ["Bisagra_Cadera", "Empuje_Vertical", "Tracción_Vertical", "Core", "Unilateral"],
    "Full Body C": ["Sentadilla", "Empuje_Horizontal", "Tracción_Vertical", "Core", "Bisagra_Cadera"],
    "Torso":       ["Empuje_Horizontal", "Empuje_Vertical", "Tracción_Horizontal", "Tracción_Vertical", "Core"],
    "Pierna":      ["Sentadilla", "Bisagra_Cadera", "Unilateral", "Core"],
    "Empuje":      ["Empuje_Horizontal", "Empuje_Vertical", "Core"],
    "Tracción":    ["Tracción_Horizontal", "Tracción_Vertical", "Core"],
}

# Configuración de mesociclos (3 meses × 4 semanas)
_MESOCICLOS = [
    {"mes": 1, "titulo": "Adaptación Anatómica", "rir": "RIR 4", "series_base": 3, "reps": "12-15"},
    {"mes": 2, "titulo": "Sobrecarga Progresiva", "rir": "RIR 3", "series_base": 4, "reps": "10-12"},
    {"mes": 3, "titulo": "Intensificación",       "rir": "RIR 2", "series_base": 4, "reps": "6-8"},
]

# Semanas de deload (última semana de cada mes)
_SEMANAS_DELOAD = {4, 8, 12}


def _filtrar_df(lesiones: str, equipo: str) -> pd.DataFrame:
    """
    Aplica filtros de seguridad y equipamiento al DataFrame global.
    Retorna un DataFrame limpio listo para selección de ejercicios.
    """
    df = DF_EJERCICIOS.copy()

    # ── Filtro de equipamiento ──
    sin_maquinas = any(w in equipo.lower() for w in ["casa", "sin", "cuerpo", "bodyweight", "peso corporal"])
    if sin_maquinas:
        df = df[df["Equipamiento"].isin(["Peso Corporal", "Mancuerna"])]

    # ── Filtros de lesión ──
    lesiones_lower = lesiones.lower()
    if any(w in lesiones_lower for w in ["lumbar", "espalda", "hernia", "disco"]):
        df = df[df["Flag_Lesion"] != "Evitar_Lumbar"]
    if any(w in lesiones_lower for w in ["rodilla", "menisco", "ligamento"]):
        df = df[df["Flag_Lesion"] != "Evitar_Rodilla"]
    if any(w in lesiones_lower for w in ["hombro", "manguito", "rotador"]):
        df = df[df["Flag_Lesion"] != "Evitar_Hombro"]

    return df.reset_index(drop=True)


def _seleccionar_ejercicios(
    df: pd.DataFrame,
    patrones: list,
    nivel: str,
    variante: int = 0,
) -> list:
    """
    Para cada patrón de movimiento requerido en la sesión, selecciona
    un ejercicio del DataFrame filtrado.

    - `variante` (0 o 1) alterna la selección para generar variabilidad
      intra-semanal entre sesiones del mismo tipo (ej: Torso A vs Torso B).
    - Prioriza ejercicios del nivel del usuario; si no hay, usa Principiante.
    - Prioriza compuestos para patrones principales, accesorios para Core.
    """
    seleccionados = []
    niveles_fallback = [nivel, "Principiante", "Intermedio", "Avanzado"]

    for patron in patrones:
        candidatos = df[df["Patron"] == patron].copy()
        if candidatos.empty:
            continue

        # Prioridad de nivel
        for lvl in niveles_fallback:
            subset = candidatos[candidatos["Nivel"] == lvl]
            if not subset.empty:
                candidatos = subset
                break

        # Para Core no forzar compuesto
        if patron != "Core":
            compuestos = candidatos[candidatos["Es_Compuesto"]]
            if not compuestos.empty:
                candidatos = compuestos

        # Variabilidad: índice rotado por variante
        idx = variante % len(candidatos)
        fila = candidatos.iloc[idx]

        seleccionados.append({
            "Ejercicio":        fila["Nombre_ES"],
            "Patron":           patron,
            "Objetivo_Tecnico": fila["Objetivo_Tecnico"],
            "_es_compuesto":    bool(fila["Es_Compuesto"]),
        })

    return seleccionados


def _aplicar_periodizacion(
    ejercicios: list,
    mes_cfg: dict,
    semana: int,
) -> list:
    """
    Aplica las reglas de periodización a una lista de ejercicios:
    - Deload en semanas 4, 8, 12: series × 0.7 redondeado, RIR 4.
    - Mes 2+: +1 serie en compuestos respecto al base.
    """
    es_deload = semana in _SEMANAS_DELOAD
    rir  = "RIR 4 (DELOAD)" if es_deload else mes_cfg["rir"]
    reps = "12-15" if es_deload else mes_cfg["reps"]

    resultado = []
    for ej in ejercicios:
        series_base = mes_cfg["series_base"]

        # +1 serie en compuestos a partir del mes 2
        if mes_cfg["mes"] >= 2 and ej.get("_es_compuesto", False):
            series_base += 1

        # Deload: reducir 30% redondeando hacia abajo
        if es_deload:
            series_base = max(2, int(series_base * 0.7))

        resultado.append({
            "Ejercicio":        ej["Ejercicio"],
            "Objetivo_Tecnico": ej["Objetivo_Tecnico"],
            "Series_Reps":      f"{series_base} x {reps}",
            "Carga":            rir,
        })

    return resultado


def _construir_entrenamiento(
    nivel: str,
    objetivo: str,
    lesiones: str,
    equipo: str,
    dias_semana: str,
) -> list:
    """
    Motor principal de periodización.

    Genera el Macrociclo completo (12 semanas) estructurado en:
      - 3 Mesociclos (meses) con progresión de RIR y volumen
      - Microciclos semanales con splits dinámicos según días disponibles
      - Deload automático en semanas 4, 8 y 12
      - Selección de ejercicios desde CSV con variabilidad intra-semanal

    Retorna lista de dicts con contrato:
      {Mes, Titulo_Mes, Semana, Semana_Label, Sesion, Ejercicio, Series_Reps, Carga, Objetivo_Tecnico}
    """
    dias_key = str(dias_semana).strip()
    if dias_key not in _SPLITS:
        dias_key = "3"  # fallback seguro

    split_sesiones = _SPLITS[dias_key]
    df_filtrado    = _filtrar_df(lesiones, equipo)

    filas: list = []
    semana_global = 0

    for mes_cfg in _MESOCICLOS:
        for semana_mes in range(1, 5):          # 4 semanas por mes
            semana_global += 1
            deload_flag = " ⚡ DELOAD" if semana_global in _SEMANAS_DELOAD else ""

            for dia_idx, nombre_sesion in enumerate(split_sesiones):
                patrones = _PATRONES_SESION.get(nombre_sesion, [])

                # variante alterna entre sesiones del mismo nombre en la semana
                # (ej: dos "Torso" en split 4 días → variante 0 y 1)
                variante = dia_idx % 2

                ejercicios_raw = _seleccionar_ejercicios(
                    df_filtrado, patrones, nivel, variante=variante
                )
                ejercicios_periodizados = _aplicar_periodizacion(
                    ejercicios_raw, mes_cfg, semana_global
                )

                label_sesion = f"Día {dia_idx + 1}: {nombre_sesion}"

                for ej in ejercicios_periodizados:
                    filas.append({
                        "Mes":              mes_cfg["mes"],
                        "Titulo_Mes":       mes_cfg["titulo"],
                        "Semana":           semana_global,
                        "Semana_Label":     f"Semana {semana_global}{deload_flag}",
                        "Sesion":           label_sesion,
                        "Ejercicio":        ej["Ejercicio"],
                        "Series_Reps":      ej["Series_Reps"],
                        "Carga":            ej["Carga"],
                        "Objetivo_Tecnico": ej["Objetivo_Tecnico"],
                    })

    return filas


def _texto_nutricion(objetivo: str, peso: float, macros: dict) -> dict:
    if "grasa" in objetivo.lower() or "quemar" in objetivo.lower():
        principal = (
            "Tu estrategia nutricional se basa en un déficit calórico moderado (-300 a -400 kcal/día) "
            "con alta ingesta proteica para preservar masa muscular mientras pierdes grasa. "
            "Prioriza alimentos de alta saciedad y bajo índice glucémico."
        )
    elif "músculo" in objetivo.lower() or "ganar" in objetivo.lower():
        principal = (
            "Tu estrategia nutricional se basa en un superávit calórico limpio (+200 a +300 kcal/día). "
            "Alta ingesta de proteína para síntesis muscular y carbohidratos periworkout "
            "para maximizar el rendimiento y la recuperación."
        )
    else:
        principal = (
            "Tu estrategia de recomposición corporal requiere comer cerca de tu mantenimiento calórico, "
            "con alta proteína para construir músculo y perder grasa simultáneamente. "
            "Es un proceso más lento pero muy efectivo para intermedios."
        )
    return {
        "principal":     principal,
        "proteinas":     f"{macros['prot_g']}g/día · Pollo, huevo, atún, legumbres, proteína en polvo",
        "carbohidratos": f"{macros['carb_g']}g/día · Avena, arroz integral, papa, frutas, verduras",
        "grasas":        f"{macros['gras_g']}g/día · Palta, aceite de oliva, frutos secos, salmón",

    }

# ─────────────────────────────────────────────
# GRÁFICOS MATPLOTLIB → BytesIO
# ─────────────────────────────────────────────
def _grafico_dona(labels: list, sizes: list, hex_colors: list, titulo: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor='white')
    wedge_props = dict(width=0.5, edgecolor='white', linewidth=2)
    ax.pie(sizes, labels=None, colors=hex_colors,
           autopct='%1.0f%%', pctdistance=0.75,
           wedgeprops=wedge_props, startangle=90,
           textprops={'fontsize': 9, 'color': '#334155'})
    ax.set_title(titulo, fontsize=10, fontweight='bold', color='#0F172A', pad=10)
    legend = ax.legend(labels, loc='lower center', bbox_to_anchor=(0.5, -0.15),
                       ncol=2, fontsize=8, frameon=False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def _grafico_macros(macros_tabla: list) -> io.BytesIO:
    labels = [r["Macro"] for r in macros_tabla]
    sizes  = [r["Porcentaje"] for r in macros_tabla]
    hexcol = [r["Color"] for r in macros_tabla]
    return _grafico_dona(labels, sizes, hexcol, "Distribución de Macros")


def _grafico_gasto(gasto_tabla: list) -> io.BytesIO:
    labels = [r["Componente"] for r in gasto_tabla]
    sizes  = [r["Porcentaje"] for r in gasto_tabla]
    hexcol = [r["Color"] for r in gasto_tabla]
    return _grafico_dona(labels, sizes, hexcol, "Gasto Energético Diario")

# ─────────────────────────────────────────────
# ESTILOS PDF
# ─────────────────────────────────────────────
def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle("titulo", parent=base["Heading1"],
                                 fontSize=22, textColor=C_PRIMARIO,
                                 spaceAfter=4, alignment=TA_CENTER),
        "subtitulo": ParagraphStyle("subtitulo", parent=base["Heading2"],
                                    fontSize=14, textColor=C_SECUNDARIO,
                                    spaceBefore=14, spaceAfter=4),
        "seccion": ParagraphStyle("seccion", parent=base["Heading3"],
                                  fontSize=11, textColor=C_PRIMARIO,
                                  spaceBefore=10, spaceAfter=4,
                                  backColor=C_FONDO_CLARO, leftIndent=6),
        "body": ParagraphStyle("body", parent=base["Normal"],
                               fontSize=9, textColor=C_TEXTO,
                               leading=14, spaceAfter=6, alignment=TA_JUSTIFY),
        "badge": ParagraphStyle("badge", parent=base["Normal"],
                                fontSize=8, textColor=C_BLANCO,
                                backColor=C_SECUNDARIO, alignment=TA_CENTER,
                                leftIndent=4, rightIndent=4),
    }
    return estilos


def _estilo_tabla_header():
    return TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), C_PRIMARIO),
        ('TEXTCOLOR',   (0, 0), (-1, 0), C_BLANCO),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 9),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_BLANCO, C_FONDO_CLARO]),
        ('FONTSIZE',    (0, 1), (-1, -1), 8),
        ('GRID',        (0, 0), (-1, -1), 0.4, C_FONDO_CLARO),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ])

# ─────────────────────────────────────────────
# GENERADOR PDF PRINCIPAL
# ─────────────────────────────────────────────
def generar_pdf_rutina(datos_usuario: dict) -> io.BytesIO:
    programa = construir_programa(datos_usuario)
    meta     = programa["_meta"]
    estilos  = _estilos()
    buffer   = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch
    )
    E = []  # elementos

    # ── PORTADA ──
    E.append(Spacer(1, 0.3*inch))
    E.append(Paragraph("RUTINATOR", estilos["titulo"]))
    E.append(Paragraph(meta["objetivo"], estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=2, color=C_SECUNDARIO, spaceAfter=8))

    # Datos atleta
    for row in programa["atleta"]:
        if row["Campo"] == "Introduccion":
            E.append(Paragraph(row["Valor"], estilos["body"]))
        elif row["Campo"] == "Titulo":
            E.append(Paragraph(row["Valor"], estilos["seccion"]))

    E.append(Spacer(1, 0.15*inch))

    # ── BIOMETRÍA ──
    E.append(Paragraph("📊 Biometría", estilos["subtitulo"]))
    bio_data = [["Indicador", "Valor"]] + \
               [[r["Indicador"], str(r["Valor"])] for r in programa["biometria"]]
    bio_tabla = Table(bio_data, colWidths=[3*inch, 2*inch])
    bio_tabla.setStyle(_estilo_tabla_header())
    E.append(bio_tabla)
    E.append(Spacer(1, 0.15*inch))

    # ── ENTRENAMIENTO por mes → semana → sesión ──
    E.append(PageBreak())
    E.append(Paragraph("🏋️ Programa de Entrenamiento — 12 Semanas", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    filas_ent = programa["entrenamiento"]

    for mes_num in [1, 2, 3]:
        filas_mes = [r for r in filas_ent if r["Mes"] == mes_num]
        if not filas_mes:
            continue

        titulo_mes = filas_mes[0]["Titulo_Mes"]
        E.append(Paragraph(f"Mes {mes_num}: {titulo_mes}", estilos["seccion"]))

        # Agrupar por semana dentro del mes
        semanas = sorted({r["Semana"] for r in filas_mes})
        for semana in semanas:
            filas_semana = [r for r in filas_mes if r["Semana"] == semana]
            semana_label = filas_semana[0]["Semana_Label"]

            # Estilo especial para semanas de deload
            es_deload = "DELOAD" in semana_label
            color_header = colors.HexColor("#F59E0B") if es_deload else C_SECUNDARIO
            E.append(Paragraph(semana_label, ParagraphStyle(
                "sem_label",
                parent=getSampleStyleSheet()["Normal"],
                fontSize=9, textColor=color_header,
                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
            )))

            # Agrupar por sesión dentro de la semana
            sesiones = sorted({r["Sesion"] for r in filas_semana},
                              key=lambda s: int(s.split(":")[0].replace("Día", "").strip()))
            for sesion in sesiones:
                filas_sesion = [r for r in filas_semana if r["Sesion"] == sesion]

                headers = ["Ejercicio", "Series/Reps", "Carga", "Objetivo Técnico"]
                rows = [headers] + [
                    [r["Ejercicio"], r["Series_Reps"], r["Carga"], r["Objetivo_Tecnico"]]
                    for r in filas_sesion
                ]
                col_w = [1.7*inch, 1.1*inch, 1.0*inch, 2.9*inch]
                t = Table(rows, colWidths=col_w)
                t.setStyle(_estilo_tabla_header())
                t.setStyle(TableStyle([('ALIGN', (3, 1), (3, -1), 'LEFT')]))

                # Encabezado de sesión como fila coloreada
                sesion_header = Table(
                    [[Paragraph(sesion, ParagraphStyle(
                        "ses_h", parent=getSampleStyleSheet()["Normal"],
                        fontSize=8, textColor=C_BLANCO, fontName="Helvetica-Bold"
                    ))]],
                    colWidths=[6.7*inch]
                )
                sesion_header.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), C_PRIMARIO),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ]))
                E.append(sesion_header)
                E.append(t)
                E.append(Spacer(1, 0.06*inch))

        E.append(Spacer(1, 0.1*inch))

    # ── NUTRICIÓN ──
    E.append(PageBreak())
    E.append(Paragraph("🥗 Estrategia Nutricional", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    for row in programa["nutricion_texto"]:
        E.append(Paragraph(f"<b>{row['Campo'].replace('_', ' ')}:</b> {row['Valor']}", estilos["body"]))

    E.append(Spacer(1, 0.15*inch))

    # Gráfico macros + tabla lado a lado
    macros_img_buf = _grafico_macros(programa["macros"])
    macros_img = Image(macros_img_buf, width=2.8*inch, height=2.8*inch)

    macros_data = [["Macro", "%", "g/día"]]
    m = meta["macros"]
    macros_data += [
        ["Proteínas",     f"{m['prot_p']}%", f"{m['prot_g']}g"],
        ["Carbohidratos", f"{m['carb_p']}%", f"{m['carb_g']}g"],
        ["Grasas",        f"{m['gras_p']}%", f"{m['gras_g']}g"],
    ]
    macros_tabla = Table(macros_data, colWidths=[1.4*inch, 0.7*inch, 0.7*inch])
    macros_tabla.setStyle(_estilo_tabla_header())

    layout_macros = Table(
        [[macros_img, macros_tabla]],
        colWidths=[3.2*inch, 3.2*inch]
    )
    layout_macros.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
    ]))
    E.append(layout_macros)
    E.append(Spacer(1, 0.2*inch))

    # ── NEAT ──
    E.append(Paragraph("🚶 NEAT — Actividad No Programada", estilos["subtitulo"]))
    for row in programa["neat_texto"]:
        E.append(Paragraph(row["Valor"], estilos["body"]))

    E.append(Spacer(1, 0.1*inch))
    neat_data = [["Estrategia"]] + [[r["Estrategia"]] for r in programa["neat_estrategias"]]
    neat_tabla = Table(neat_data, colWidths=[6.8*inch])
    neat_tabla.setStyle(_estilo_tabla_header())
    E.append(neat_tabla)
    E.append(Spacer(1, 0.2*inch))

    # Gráfico gasto energético
    gasto_img_buf = _grafico_gasto(programa["gasto_energetico"])
    gasto_img = Image(gasto_img_buf, width=3.0*inch, height=3.0*inch)

    gasto_data = [["Componente", "%"]] + \
                 [[r["Componente"], f"{r['Porcentaje']}%"] for r in programa["gasto_energetico"]]
    gasto_tabla = Table(gasto_data, colWidths=[1.6*inch, 0.8*inch])
    gasto_tabla.setStyle(_estilo_tabla_header())

    layout_gasto = Table(
        [[gasto_img, gasto_tabla]],
        colWidths=[3.4*inch, 3.0*inch]
    )
    layout_gasto.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
    ]))
    E.append(layout_gasto)

    doc.build(E)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# REVISTA NUTRICIONAL (PDF 2)
# ─────────────────────────────────────────────
def generar_revista_nutricional(datos_usuario: dict) -> io.BytesIO:
    programa = construir_programa(datos_usuario)
    meta     = programa["_meta"]
    estilos  = _estilos()
    buffer   = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch
    )
    E = []

    E.append(Paragraph("COME COMO ENTRENAS", estilos["titulo"]))
    E.append(Paragraph(f"Edición personalizada · {meta['nombre']}", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=2, color=C_ACENTO, spaceAfter=10))

    # Estrategia
    for row in programa["nutricion_texto"]:
        E.append(Paragraph(f"<b>{row['Campo'].replace('_', ' ')}:</b>", estilos["seccion"]))
        E.append(Paragraph(row["Valor"], estilos["body"]))

    E.append(Spacer(1, 0.2*inch))

    # Alimentos recomendados por categoría
    E.append(Paragraph("🛒 Guía de Compras Semanal", estilos["subtitulo"]))
    alimentos = [
        ["Categoría", "Alimentos Recomendados", "Frecuencia"],
        ["Proteína animal", "Pollo, pavo, huevos, atún, salmón, sardinas", "Diaria"],
        ["Proteína vegetal", "Lentejas, garbanzos, tofu, edamame", "3-4x/semana"],
        ["Carbohidratos", "Avena, arroz integral, papa, camote, quinoa", "Diaria"],
        ["Frutas", "Plátano, manzana, berries, naranja, kiwi", "2 porciones/día"],
        ["Verduras", "Espinaca, brócoli, zanahoria, tomate, pepino", "Abundante"],
        ["Grasas saludables", "Palta, aceite de oliva, nueces, almendras", "Diaria"],
        ["Hidratación", "Agua, té verde, café sin azúcar", "2-3L/día"],
    ]
    t = Table(alimentos, colWidths=[1.5*inch, 3.5*inch, 1.8*inch])
    t.setStyle(_estilo_tabla_header())
    E.append(t)

    E.append(Spacer(1, 0.2*inch))
    E.append(Paragraph("💡 Reglas de Oro", estilos["subtitulo"]))
    reglas = [
        "Come proteína en cada comida principal.",
        "Carbohidratos complejos antes y después del entrenamiento.",
        "No elimines grupos alimentarios: ajusta porciones.",
        "Prepara comidas con anticipación (meal prep dominical).",
        "Duerme 7-9 horas: el músculo se construye en el descanso.",
    ]
    for r in reglas:
        E.append(Paragraph(f"• {r}", estilos["body"]))

    doc.build(E)
    buffer.seek(0)
    return buffer
