"""
Generador de PDF de rutina completa (12 semanas).
Usa la nueva arquitectura — sin dependencia de logic_processor.
"""
import io
import logging

import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.application import get_training_generator_service
from src.domain.rules import generar_estrategias_neat, generar_intro_neat

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

# ── Paleta de colores ──
C_PRIMARIO = colors.HexColor("#0F172A")
C_SECUNDARIO = colors.HexColor("#2563EB")
C_ACENTO = colors.HexColor("#10B981")
C_TEXTO = colors.HexColor("#334155")
C_FONDO_CLARO = colors.HexColor("#E2E8F0")
C_BLANCO = colors.white
C_ROJO = colors.HexColor("#E11D48")
C_AMARILLO = colors.HexColor("#F59E0B")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Heading1"],
            fontSize=22, textColor=C_PRIMARIO,
            spaceAfter=4, alignment=TA_CENTER,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Heading2"],
            fontSize=14, textColor=C_SECUNDARIO,
            spaceBefore=14, spaceAfter=4,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Heading3"],
            fontSize=11, textColor=C_PRIMARIO,
            spaceBefore=10, spaceAfter=4,
            backColor=C_FONDO_CLARO, leftIndent=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=C_TEXTO,
            leading=14, spaceAfter=6, alignment=TA_JUSTIFY,
        ),
    }


def _estilo_tabla_header() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_BLANCO, C_FONDO_CLARO]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, C_FONDO_CLARO),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _grafico_dona(labels: list, sizes: list, hex_colors: list, titulo: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor="white")
    wedge_props = {"width": 0.5, "edgecolor": "white", "linewidth": 2}
    ax.pie(
        sizes, labels=None, colors=hex_colors,
        autopct="%1.0f%%", pctdistance=0.75,
        wedgeprops=wedge_props, startangle=90,
        textprops={"fontsize": 9, "color": "#334155"},
    )
    ax.set_title(titulo, fontsize=10, fontweight="bold", color="#0F172A", pad=10)
    ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.15),
              ncol=2, fontsize=8, frameon=False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def generar_pdf_rutina_sync(datos_usuario: dict) -> io.BytesIO:
    """
    Genera PDF de rutina completa (12 semanas).
    Función síncrona para usar con async_bridge.

    Args:
        datos_usuario: Diccionario con datos del atleta

    Returns:
        BytesIO con el PDF generado
    """
    service = get_training_generator_service()
    programa = service.generar_programa_desde_dict(datos_usuario)

    athlete = programa.athlete
    bio = programa.biometria
    macros = programa.macros
    gasto = programa.gasto
    nutricion = programa.nutricion
    semanas = programa.semanas

    estilos = _estilos()
    base_styles = getSampleStyleSheet()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
    )
    E = []

    # ── PORTADA ──
    E.append(Spacer(1, 0.3 * inch))
    E.append(Paragraph("RUTINATOR", estilos["titulo"]))
    E.append(Paragraph(athlete.objetivo.value, estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=2, color=C_SECUNDARIO, spaceAfter=8))

    titulo_plan = f"Plan Trimestral · {athlete.objetivo.value} · {athlete.nivel.value}"
    E.append(Paragraph(titulo_plan, estilos["seccion"]))

    intro = (
        f"Hola {athlete.nombre}, este es tu programa de 12 semanas diseñado específicamente "
        f"para tu objetivo de {athlete.objetivo.value.lower()}. Trabajaremos en tres fases progresivas: "
        f"adaptación anatómica, volumen y finalmente intensificación. "
        f"Cada semana tiene un propósito claro. Confía en el proceso."
    )
    E.append(Paragraph(intro, estilos["body"]))
    E.append(Spacer(1, 0.15 * inch))

    # ── BIOMETRÍA ──
    E.append(Paragraph("📊 Biometría", estilos["subtitulo"]))
    bio_data = [
        ["Indicador", "Valor"],
        ["Peso (kg)", str(bio.peso)],
        ["Altura (cm)", str(bio.talla)],
        ["IMC", str(bio.imc)],
        ["% Masa Muscular", str(bio.masa_muscular)],
        ["% Agua", str(bio.agua)],
        ["% Grasa Visceral", str(bio.grasa_visceral)],
    ]
    bio_tabla = Table(bio_data, colWidths=[3 * inch, 2 * inch])
    bio_tabla.setStyle(_estilo_tabla_header())
    E.append(bio_tabla)
    E.append(Spacer(1, 0.15 * inch))

    # ── ENTRENAMIENTO 12 SEMANAS ──
    E.append(PageBreak())
    E.append(Paragraph("🏋️ Programa de Entrenamiento — 12 Semanas", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    # Agrupar semanas por bloque (mes)
    from src.domain.models import BloqueATR
    bloques = [
        (BloqueATR.ACUMULACION, "Mes 1: Acumulación (Volumen Alto)", range(1, 5)),
        (BloqueATR.TRANSMUTACION, "Mes 2: Transmutación (Intensidad Alta)", range(5, 9)),
        (BloqueATR.REALIZACION, "Mes 3: Realización (Intensidad Máxima)", range(9, 13)),
    ]

    for _bloque, titulo_mes, rango in bloques:
        semanas_bloque = [s for s in semanas if s.numero in rango]
        if not semanas_bloque:
            continue

        E.append(Paragraph(titulo_mes, estilos["seccion"]))

        for semana in semanas_bloque:
            color_header = C_AMARILLO if semana.es_deload else C_SECUNDARIO
            deload_label = " ⚡ DELOAD" if semana.es_deload else ""
            E.append(Paragraph(
                f"Semana {semana.numero}{deload_label}",
                ParagraphStyle(
                    "sem_label", parent=base_styles["Normal"],
                    fontSize=9, textColor=color_header,
                    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
                ),
            ))

            for sesion in semana.sesiones:
                label = f"Día {sesion.dia}: {sesion.nombre_sesion}"
                sesion_header = Table(
                    [[Paragraph(label, ParagraphStyle(
                        "ses_h", parent=base_styles["Normal"],
                        fontSize=8, textColor=C_BLANCO, fontName="Helvetica-Bold",
                    ))]],
                    colWidths=[6.7 * inch],
                )
                sesion_header.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), C_PRIMARIO),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]))
                E.append(sesion_header)

                headers = ["Ejercicio", "Series/Reps Objetivo", "Carga Sugerida", "Objetivo Técnico"]
                rows = [headers] + [
                    [ej.nombre, ej.series_reps, ej.carga, ej.objetivo_tecnico]
                    for ej in sesion.ejercicios
                ]
                col_w = [1.7 * inch, 1.3 * inch, 1.1 * inch, 2.6 * inch]
                t = Table(rows, colWidths=col_w)
                t.setStyle(_estilo_tabla_header())
                t.setStyle(TableStyle([("ALIGN", (3, 1), (3, -1), "LEFT")]))
                E.append(t)
                E.append(Spacer(1, 0.06 * inch))

        E.append(Spacer(1, 0.1 * inch))

    # ── NUTRICIÓN ──
    E.append(PageBreak())
    E.append(Paragraph("🥗 Estrategia Nutricional", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    E.append(Paragraph(f"<b>Estrategia Principal:</b> {nutricion.estrategia_principal}", estilos["body"]))
    E.append(Paragraph(f"<b>Proteínas:</b> {nutricion.proteinas}", estilos["body"]))
    E.append(Paragraph(f"<b>Carbohidratos:</b> {nutricion.carbohidratos}", estilos["body"]))
    E.append(Paragraph(f"<b>Grasas:</b> {nutricion.grasas}", estilos["body"]))
    E.append(Spacer(1, 0.15 * inch))

    # Gráfico macros
    macros_img_buf = _grafico_dona(
        ["Proteínas", "Carbohidratos", "Grasas"],
        [macros.prot_p, macros.carb_p, macros.gras_p],
        ["#E11D48", "#2563EB", "#F59E0B"],
        "Distribución de Macros",
    )
    macros_img = Image(macros_img_buf, width=2.8 * inch, height=2.8 * inch)

    macros_tabla_data = [
        ["Macro", "%", "g/día"],
        ["Proteínas", f"{macros.prot_p}%", f"{macros.prot_g}g"],
        ["Carbohidratos", f"{macros.carb_p}%", f"{macros.carb_g}g"],
        ["Grasas", f"{macros.gras_p}%", f"{macros.gras_g}g"],
    ]
    macros_tabla = Table(macros_tabla_data, colWidths=[1.4 * inch, 0.7 * inch, 0.7 * inch])
    macros_tabla.setStyle(_estilo_tabla_header())

    layout_macros = Table([[macros_img, macros_tabla]], colWidths=[3.2 * inch, 3.2 * inch])
    layout_macros.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    E.append(layout_macros)
    E.append(Spacer(1, 0.2 * inch))

    # ── NEAT ──
    E.append(Paragraph("🚶 NEAT — Actividad No Programada", estilos["subtitulo"]))
    E.append(Paragraph(generar_intro_neat(athlete.objetivo.value), estilos["body"]))
    E.append(Spacer(1, 0.1 * inch))

    neat_data = [["Estrategia"]] + [[e] for e in generar_estrategias_neat()]
    neat_tabla = Table(neat_data, colWidths=[6.8 * inch])
    neat_tabla.setStyle(_estilo_tabla_header())
    E.append(neat_tabla)
    E.append(Spacer(1, 0.2 * inch))

    # Gráfico gasto energético
    gasto_img_buf = _grafico_dona(
        ["TMB", "NEAT", "Ejercicio", "TEF"],
        [gasto.tmb, gasto.neat, gasto.ejercicio, gasto.tef],
        ["#0F172A", "#2563EB", "#10B981", "#F59E0B"],
        "Gasto Energético Diario",
    )
    gasto_img = Image(gasto_img_buf, width=3.0 * inch, height=3.0 * inch)

    gasto_tabla_data = [
        ["Componente", "%"],
        ["TMB", f"{gasto.tmb}%"],
        ["NEAT", f"{gasto.neat}%"],
        ["Ejercicio", f"{gasto.ejercicio}%"],
        ["TEF", f"{gasto.tef}%"],
    ]
    gasto_tabla = Table(gasto_tabla_data, colWidths=[1.6 * inch, 0.8 * inch])
    gasto_tabla.setStyle(_estilo_tabla_header())

    layout_gasto = Table([[gasto_img, gasto_tabla]], colWidths=[3.4 * inch, 3.0 * inch])
    layout_gasto.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    E.append(layout_gasto)

    doc.build(E)
    buffer.seek(0)
    return buffer


generar_pdf_rutina = generar_pdf_rutina_sync
