import io
import math
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
    tabla_entrenamiento = _construir_entrenamiento(nivel, objetivo, lesiones, equipo)

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
# CONSTRUCCIÓN DEL ENTRENAMIENTO (Tabla 3)
# ─────────────────────────────────────────────
def _construir_entrenamiento(nivel: str, objetivo: str, lesiones: str, equipo: str) -> list:
    """Genera filas de entrenamiento para los 3 meses según perfil."""
    lesion_lumbar = any(w in lesiones.lower() for w in ["lumbar", "espalda", "hernia", "disco"])
    lesion_rodilla = any(w in lesiones.lower() for w in ["rodilla", "menisco", "ligamento"])
    lesion_hombro = any(w in lesiones.lower() for w in ["hombro", "manguito", "rotador"])
    sin_equipo = any(w in equipo.lower() for w in ["casa", "sin", "cuerpo", "bodyweight"])

    # Selección de ejercicios según restricciones
    squat = "Sentadilla Goblet" if lesion_lumbar else "Sentadilla Libre"
    hip_hinge = "Hip Thrust" if lesion_lumbar else "Peso Muerto Rumano"
    empuje_h = "Flexiones" if (lesion_hombro or sin_equipo) else "Press Banca"
    empuje_v = "Elevaciones Laterales" if lesion_hombro else ("Press Militar Mancuernas" if sin_equipo else "Press Militar Barra")
    traccion_h = "Remo en TRX" if sin_equipo else "Remo con Mancuerna"
    traccion_v = "Jalón al Pecho" if not sin_equipo else "Dominadas Asistidas"
    unilateral = "Zancada Estática" if lesion_rodilla else "Zancada Caminando"

    filas = []

    # MES 1 — Adaptación anatómica
    mes1 = [
        (squat,        "3 x 12-15", "RIR 4", "Pecho arriba, rodillas sobre pies, pausa 1s abajo"),
        (hip_hinge,    "3 x 12",    "RIR 4", "Bisagra de cadera, espalda neutra, empuje de talones"),
        (empuje_h,     "3 x 12-15", "RIR 4", "Escápulas retraídas, codos a 45°"),
        (traccion_h,   "3 x 12-15", "RIR 4", "Codo pegado al cuerpo, retracción escapular"),
        (empuje_v,     "3 x 12",    "RIR 4", "Core activo, no arquear lumbar"),
        (traccion_v,   "3 x 12",    "RIR 4", "Tirar con codos, no con manos"),
        ("Plancha",    "3 x 30-45s","Tiempo", "Cuerpo recto, glúteos activos, respiración"),
        (unilateral,   "3 x 10/lado","RIR 4", "Rodilla delantera no supera punta del pie"),
    ]
    for ej, sr, peso, obj_tec in mes1:
        filas.append({"Mes": 1, "Titulo_Mes": "Adaptación Anatómica",
                      "Ejercicio": ej, "Series_Reps": sr,
                      "Peso": peso, "Objetivo_Tecnico": obj_tec})

    # MES 2 — Volumen / Hipertrofia
    mes2 = [
        (squat,        "4 x 10-12", "RIR 3", "Aumentar ROM progresivamente"),
        (hip_hinge,    "4 x 10",    "RIR 3", "Controlar excéntrico 3 segundos"),
        (empuje_h,     "4 x 10-12", "RIR 3", "Rango completo, pausa en pecho"),
        (traccion_h,   "4 x 10-12", "RIR 3", "Squeeze en contracción máxima"),
        (empuje_v,     "4 x 10",    "RIR 3", "Progresión de carga si técnica es sólida"),
        (traccion_v,   "4 x 10",    "RIR 3", "Depresión escapular antes de tirar"),
        ("Plancha Dinámica", "3 x 40s", "Tiempo", "Alternar elevación de pierna/brazo"),
        (unilateral,   "3 x 12/lado","RIR 3", "Añadir mancuerna si hay control"),
        ("Face Pull",  "3 x 15",    "RIR 3", "Salud de hombro, codos altos"),
    ]
    for ej, sr, peso, obj_tec in mes2:
        filas.append({"Mes": 2, "Titulo_Mes": "Volumen e Hipertrofia",
                      "Ejercicio": ej, "Series_Reps": sr,
                      "Peso": peso, "Objetivo_Tecnico": obj_tec})

    # MES 3 — Intensificación
    mes3 = [
        (squat,        "4 x 6-8",   "RIR 2", "Velocidad intencional en concéntrico"),
        (hip_hinge,    "4 x 6-8",   "RIR 2", "Carga máxima con técnica impecable"),
        (empuje_h,     "4 x 6-8",   "RIR 2", "Progresión de carga semanal +2.5kg"),
        (traccion_h,   "4 x 8",     "RIR 2", "Añadir lastre o banda de resistencia"),
        (empuje_v,     "4 x 8",     "RIR 2", "Tempo 2-0-1, explosivo en subida"),
        (traccion_v,   "4 x 8",     "RIR 2", "Peso máximo con rango completo"),
        ("Ab Wheel",   "3 x 10",    "RIR 2", "Core antiextensión, no hundir lumbar"),
        (unilateral,   "4 x 10/lado","RIR 2","Mancuerna en cada mano"),
        ("Face Pull",  "3 x 12",    "RIR 2", "Mantenimiento salud articular"),
    ]
    for ej, sr, peso, obj_tec in mes3:
        filas.append({"Mes": 3, "Titulo_Mes": "Intensificación",
                      "Ejercicio": ej, "Series_Reps": sr,
                      "Peso": peso, "Objetivo_Tecnico": obj_tec})

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

    # ── ENTRENAMIENTO por mes ──
    E.append(PageBreak())
    E.append(Paragraph("🏋️ Programa de Entrenamiento — 12 Semanas", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    for mes_num in [1, 2, 3]:
        filas_mes = [r for r in programa["entrenamiento"] if r["Mes"] == mes_num]
        if not filas_mes:
            continue
        titulo_mes = filas_mes[0]["Titulo_Mes"]
        E.append(Paragraph(f"Mes {mes_num}: {titulo_mes}", estilos["seccion"]))

        headers = ["Ejercicio", "Series/Reps", "Carga", "Objetivo Técnico"]
        rows = [headers] + [
            [r["Ejercicio"], r["Series_Reps"], r["Peso"], r["Objetivo_Tecnico"]]
            for r in filas_mes
        ]
        col_w = [1.8*inch, 1.1*inch, 0.9*inch, 3.0*inch]
        t = Table(rows, colWidths=col_w)
        t.setStyle(_estilo_tabla_header())
        # Alinear objetivo técnico a la izquierda
        t.setStyle(TableStyle([('ALIGN', (3, 1), (3, -1), 'LEFT')]))
        E.append(t)
        E.append(Spacer(1, 0.12*inch))

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
