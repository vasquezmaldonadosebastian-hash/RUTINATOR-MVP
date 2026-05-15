"""
Base styles y helpers para generación de PDFs.
Extrae la lógica de estilos de logic_processor.py original.
"""
from dataclasses import dataclass
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle


@dataclass
class PDFStyles:
    """Contenedor de estilos para PDFs."""
    titulo: ParagraphStyle
    subtitulo: ParagraphStyle
    seccion: ParagraphStyle
    body: ParagraphStyle
    badge: ParagraphStyle

    # Colores
    primario: colors.Color
    secundario: colors.Color
    acento: colors.Color
    texto: colors.Color
    fondo_claro: colors.Color
    blanco: colors.Color
    rojo: colors.Color
    amarillo: colors.Color


def get_pdf_styles() -> PDFStyles:
    """Crea estilos para PDFs estándar."""
    base = getSampleStyleSheet()

    # Colores
    primario = colors.HexColor("#0F172A")
    secundario = colors.HexColor("#2563EB")
    acento = colors.HexColor("#10B981")
    texto = colors.HexColor("#334155")
    fondo_claro = colors.HexColor("#E2E8F0")
    blanco = colors.white
    rojo = colors.HexColor("#E11D48")
    amarillo = colors.HexColor("#F59E0B")

    return PDFStyles(
        titulo=ParagraphStyle(
            "titulo", parent=base["Heading1"],
            fontSize=22, textColor=primario,
            spaceAfter=4, alignment=TA_CENTER
        ),
        subtitulo=ParagraphStyle(
            "subtitulo", parent=base["Heading2"],
            fontSize=14, textColor=secundario,
            spaceBefore=14, spaceAfter=4
        ),
        seccion=ParagraphStyle(
            "seccion", parent=base["Heading3"],
            fontSize=11, textColor=primario,
            spaceBefore=10, spaceAfter=4,
            backColor=fondo_claro, leftIndent=6
        ),
        body=ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=texto,
            leading=14, spaceAfter=6, alignment=TA_JUSTIFY
        ),
        badge=ParagraphStyle(
            "badge", parent=base["Normal"],
            fontSize=8, textColor=blanco,
            backColor=secundario, alignment=TA_CENTER,
            leftIndent=4, rightIndent=4
        ),
        primario=primario,
        secundario=secundario,
        acento=acento,
        texto=texto,
        fondo_claro=fondo_claro,
        blanco=blanco,
        rojo=rojo,
        amarillo=amarillo,
    )


def get_tabla_estilo_header() -> TableStyle:
    """Estilo estándar para headers de tabla."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E2E8F0")]),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])


def get_doc_config() -> dict:
    """Configuración base para SimpleDocTemplate."""
    return {
        "pagesize": letter,
        "leftMargin": 0.6 * inch,
        "rightMargin": 0.6 * inch,
        "topMargin": 0.6 * inch,
        "bottomMargin": 0.6 * inch,
    }


# Estilos para revista nutricional editorial
def get_editorial_styles() -> dict[str, Any]:
    """Estilos para revista nutricional con diseño editorial oscuro."""
    base = getSampleStyleSheet()

    # Colores editorial
    fondo_oscuro = colors.HexColor("#0E1113")
    fondo_secundario = colors.HexColor("#1B1F24")
    texto_blanco = colors.white
    acento_verde = colors.HexColor("#6E9F45")
    acento_rojo = colors.HexColor("#8B1E2D")
    acento_amarillo = colors.HexColor("#F59E0B")

    return {
        "fondo_oscuro": fondo_oscuro,
        "fondo_secundario": fondo_secundario,
        "texto_blanco": texto_blanco,
        "acento_verde": acento_verde,
        "acento_rojo": acento_rojo,
        "acento_amarillo": acento_amarillo,
        "titulo_editorial": ParagraphStyle(
            "titulo_editorial", parent=base["Heading1"],
            fontSize=28, textColor=texto_blanco,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceAfter=12
        ),
        "subtitulo_editorial": ParagraphStyle(
            "subtitulo_editorial", parent=base["Heading2"],
            fontSize=18, textColor=acento_verde,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceBefore=16, spaceAfter=8
        ),
        "seccion_editorial": ParagraphStyle(
            "seccion_editorial", parent=base["Heading3"],
            fontSize=14, textColor=acento_amarillo,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
            leftIndent=10
        ),
        "body_editorial": ParagraphStyle(
            "body_editorial", parent=base["Normal"],
            fontSize=10, textColor=texto_blanco,
            leading=16, spaceAfter=8, alignment=TA_JUSTIFY
        ),
    }
