"""
Generador de PDF de rutina semanal con feedback.
Usa la nueva arquitectura — sin dependencia de logic_processor.
"""
import io
import logging

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.application import get_training_generator_service
from src.domain.rules import es_semana_deload, obtener_bloque_desde_semana

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

# ── Paleta de colores ──
C_PRIMARIO = colors.HexColor("#0F172A")
C_SECUNDARIO = colors.HexColor("#2563EB")
C_FONDO_CLARO = colors.HexColor("#E2E8F0")
C_BLANCO = colors.white
C_ROJO = colors.HexColor("#E11D48")
C_AMARILLO = colors.HexColor("#F59E0B")
C_FEEDBACK = colors.HexColor("#F0F9FF")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Heading1"],
            fontSize=20, textColor=C_PRIMARIO,
            spaceAfter=4, alignment=TA_CENTER,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Heading2"],
            fontSize=13, textColor=C_SECUNDARIO,
            spaceBefore=12, spaceAfter=4,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Heading3"],
            fontSize=10, textColor=C_PRIMARIO,
            spaceBefore=8, spaceAfter=4,
            backColor=C_FONDO_CLARO, leftIndent=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=colors.HexColor("#334155"),
            leading=14, spaceAfter=6,
        ),
        "deload": ParagraphStyle(
            "deload", parent=base["Normal"],
            fontSize=9, textColor=C_ROJO,
            leading=14, spaceAfter=6,
        ),
    }


def _estilo_feedback() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_BLANCO, C_FONDO_CLARO]),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, C_FONDO_CLARO),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (3, 1), (5, -1), C_FEEDBACK),
    ])


def generar_rutina_semanal_sync(datos_usuario: dict) -> io.BytesIO:
    """
    Genera PDF de rutina semanal con columnas de feedback.
    Función síncrona para usar con async_bridge.

    Args:
        datos_usuario: Diccionario con datos del atleta

    Returns:
        BytesIO con el PDF generado
    """
    service = get_training_generator_service()
    semana_num = int(datos_usuario.get("semana_actual", 1))

    # Generar programa para la semana específica
    programa = service.generar_programa_desde_dict({**datos_usuario, "semana_actual": semana_num})
    athlete = programa.athlete
    semana = programa.semanas[0] if programa.semanas else None

    if not semana:
        raise ValueError(f"No se pudo generar la semana {semana_num}")

    bloque = obtener_bloque_desde_semana(semana_num)
    es_deload = es_semana_deload(semana_num)

    estilos = _estilos()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
    )
    E = []

    # ── PORTADA SEMANAL ──
    E.append(Spacer(1, 0.2 * inch))
    E.append(Paragraph(
        f"RUTINA SEMANAL · BLOQUE {bloque.value.upper()}",
        estilos["titulo"],
    ))
    E.append(Paragraph(
        f"Semana {semana_num} · {athlete.nombre}",
        estilos["subtitulo"],
    ))
    E.append(HRFlowable(width="100%", thickness=2, color=C_SECUNDARIO, spaceAfter=8))

    # Info del bloque ATR
    from src.domain.rules import obtener_config_semana
    config = obtener_config_semana(semana_num)
    info_bloque = (
        f"<b>Bloque:</b> {config.bloque.value} · "
        f"<b>Volumen:</b> {config.volumen} · "
        f"<b>Intensidad:</b> {config.intensidad}<br/>"
        f"<b>RIR Objetivo:</b> {config.rir} · "
        f"<b>Series Base:</b> {config.series_base} · "
        f"<b>Reps:</b> {config.reps}"
    )
    E.append(Paragraph(info_bloque, estilos["body"]))

    if es_deload:
        E.append(Paragraph(
            "⚠️ <b>SEMANA DE DELOAD</b> · Reducción del 30% en volumen para recuperación",
            estilos["deload"],
        ))

    E.append(Spacer(1, 0.15 * inch))

    # ── TABLA DE ENTRENAMIENTO CON FEEDBACK ──
    base_styles = getSampleStyleSheet()

    for sesion in semana.sesiones:
        # Encabezado de sesión
        label = f"Día {sesion.dia}: {sesion.nombre_sesion}"
        sesion_header = Table(
            [[Paragraph(label, ParagraphStyle(
                "ses_h", parent=base_styles["Normal"],
                fontSize=9, textColor=C_BLANCO, fontName="Helvetica-Bold",
            ))]],
            colWidths=[6.8 * inch],
        )
        sesion_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_PRIMARIO),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        E.append(sesion_header)
        E.append(Spacer(1, 0.06 * inch))

        # Tabla con columnas de feedback
        headers = [
            "Ejercicio", "Series/Reps Objetivo", "Carga Sugerida",
            "Reps Logradas", "Carga Real", "Comentarios",
        ]
        rows = [headers]
        for ej in sesion.ejercicios:
            rows.append([
                ej.nombre,
                ej.series_reps,
                ej.carga,
                "_____",
                "_____",
                "________________________",
            ])

        col_w = [1.4 * inch, 1.0 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 1.9 * inch]
        t = Table(rows, colWidths=col_w)
        t.setStyle(_estilo_feedback())
        E.append(t)
        E.append(Spacer(1, 0.15 * inch))

    # ── INSTRUCCIONES DE FEEDBACK ──
    E.append(PageBreak())
    E.append(Paragraph("📝 INSTRUCCIONES PARA EL FEEDBACK", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=1, color=C_FONDO_CLARO, spaceAfter=6))

    instrucciones = [
        "1. <b>Reps Logradas:</b> Anota cuántas repeticiones completaste realmente en cada serie.",
        "2. <b>Carga Real:</b> Registra el peso que usaste (ej: 20kg, 45lb, banda media).",
        "3. <b>Comentarios:</b> Escribe cómo te sentiste: 'Fácil', 'Retador', 'Dolor en hombro', etc.",
        "4. <b>Progresión:</b> Si completaste todas las reps con RIR > objetivo, sube 2.5-5% la próxima semana.",
        "5. <b>Deload:</b> En semanas 4, 8 y 12 reduce volumen 30%. No intentes batir récords.",
    ]
    for instr in instrucciones:
        E.append(Paragraph(instr, estilos["body"]))
        E.append(Spacer(1, 0.05 * inch))

    E.append(Spacer(1, 0.1 * inch))
    E.append(Paragraph("<b>OBJETIVO DEL BLOQUE ACTUAL:</b>", estilos["seccion"]))

    objetivos_bloque = {
        "Acumulación": "Adaptación anatómica y acumulación de volumen. Enfócate en técnica y rango completo.",
        "Transmutación": "Transición a mayor intensidad. Mantén buena forma mientras aumentas carga.",
        "Realización": "Expresión de fuerza máxima. Descansa bien y enfócate en intensidad, no volumen.",
    }
    E.append(Paragraph(objetivos_bloque.get(bloque.value, ""), estilos["body"]))

    doc.build(E)
    buffer.seek(0)
    return buffer


generar_rutina_semanal = generar_rutina_semanal_sync
