"""
Generador de PDF de revista nutricional editorial.
Usa la nueva arquitectura — sin dependencia de logic_processor.
"""
import io
import logging

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
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

logger = logging.getLogger(__name__)

# ── Paleta editorial oscura ──
C_FONDO_OSCURO = colors.HexColor("#0E1113")
C_FONDO_SECUNDARIO = colors.HexColor("#1B1F24")
C_TEXTO_BLANCO = colors.white
C_ACENTO_VERDE = colors.HexColor("#6E9F45")
C_ACENTO_ROJO = colors.HexColor("#8B1E2D")
C_ACENTO_AMARILLO = colors.HexColor("#F59E0B")


def _estilos_editoriales() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo_ed", parent=base["Heading1"],
            fontSize=28, textColor=C_TEXTO_BLANCO,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo_ed", parent=base["Heading2"],
            fontSize=18, textColor=C_ACENTO_VERDE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
            spaceBefore=16, spaceAfter=8,
        ),
        "seccion": ParagraphStyle(
            "seccion_ed", parent=base["Heading3"],
            fontSize=14, textColor=C_ACENTO_AMARILLO,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
            leftIndent=10,
        ),
        "body": ParagraphStyle(
            "body_ed", parent=base["Normal"],
            fontSize=10, textColor=C_TEXTO_BLANCO,
            leading=16, spaceAfter=8, alignment=TA_JUSTIFY,
            fontName="Helvetica",
        ),
        "quote": ParagraphStyle(
            "quote_ed", parent=base["Normal"],
            fontSize=11, textColor=C_ACENTO_VERDE,
            fontName="Helvetica-Oblique", leftIndent=20, rightIndent=20,
            spaceBefore=10, spaceAfter=10, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer_ed", parent=base["Normal"],
            fontSize=7, textColor=C_ACENTO_VERDE, alignment=TA_CENTER,
        ),
    }


def _estilo_tabla_editorial() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_ACENTO_VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_TEXTO_BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_FONDO_SECUNDARIO, C_FONDO_OSCURO]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, C_ACENTO_ROJO),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXTO_BLANCO),
    ])


def generar_revista_nutricional_sync(datos_usuario: dict) -> io.BytesIO:
    """
    Genera PDF de revista nutricional con diseño editorial oscuro.
    Función síncrona para usar con async_bridge.

    Args:
        datos_usuario: Diccionario con datos del atleta

    Returns:
        BytesIO con el PDF generado
    """
    service = get_training_generator_service()
    programa = service.generar_programa_desde_dict(datos_usuario)

    athlete = programa.athlete
    macros = programa.macros
    nutricion = programa.nutricion
    objetivo = athlete.objetivo.value

    estilos = _estilos_editoriales()
    estilo_tabla = _estilo_tabla_editorial()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    )
    E = []

    # ── PORTADA EDITORIAL ──
    E.append(Spacer(1, 1.5 * inch))
    E.append(Paragraph("NUTRICIÓN DEPORTIVA", estilos["titulo"]))
    E.append(Paragraph("EDICIÓN EDITORIAL", estilos["subtitulo"]))
    E.append(HRFlowable(width="80%", thickness=3, color=C_ACENTO_ROJO, spaceAfter=20))
    E.append(Paragraph(f"PARA {athlete.nombre.upper()}", estilos["seccion"]))
    E.append(Paragraph(f"OBJETIVO: {objetivo.upper()}", estilos["body"]))
    E.append(PageBreak())

    # ── PARTE A: ALIMENTACIÓN ANTIINFLAMATORIA ──
    E.append(Paragraph("ALIMENTACIÓN ANTIINFLAMATORIA", estilos["seccion"]))
    E.append(Spacer(1, 0.2 * inch))

    intro = (
        "La inflamación crónica de bajo grado es el enemigo silencioso del rendimiento y la recuperación. "
        "Una dieta rica en alimentos antiinflamatorios no solo acelera la reparación muscular, "
        "sino que optimiza la composición corporal y la salud metabólica."
    )
    E.append(Paragraph(intro, estilos["body"]))
    E.append(Spacer(1, 0.15 * inch))

    E.append(Paragraph("ALIMENTOS ANTIINFLAMATORIOS LOCALES", estilos["seccion"]))

    alimentos = [
        ["Alimento", "Beneficio", "Forma de Consumo"],
        ["Maqui", "ORAC extremo (antioxidante 10× arándanos)", "Polvo en smoothies, 1 cucharadita/día"],
        ["Murta", "Antocianinas neuroprotectoras", "Fresca o congelada, ½ taza post-entreno"],
        ["Jurel", "Omega-3 EPA/DHA, proteína magra", "Filete a la plancha, 2×/semana"],
        ["Salmón", "Astaxantina + Omega-3", "Salvaje preferible, 150g 2×/semana"],
        ["Aceite de Canola", "Omega-3 ALA, ratio ω6:ω3 ideal", "1 cucharada en ensaladas"],
        ["Quinua", "Proteína completa, quercetina", "Sustituto de arroz, ½ taza cocida"],
        ["Brócoli", "Sulforafano (detox hepático)", "Al vapor o salteado, diario"],
        ["Cúrcuma", "Curcumina (inhibidor NF‑κB)", "1 cucharadita + pimienta negra"],
    ]
    t_alimentos = Table(alimentos, colWidths=[1.8 * inch, 2.5 * inch, 2.3 * inch])
    t_alimentos.setStyle(estilo_tabla)
    E.append(t_alimentos)
    E.append(Spacer(1, 0.2 * inch))

    cita = "«NO SE TRATA DE DIETAS, SINO DE HÁBITOS. NO SE TRATA DE RESTRICCIÓN, SINO DE NUTRICIÓN.»"
    E.append(Paragraph(cita, estilos["quote"]))
    E.append(PageBreak())

    # ── PARTE B: PLAN ESPECÍFICO DEL ATLETA ──
    E.append(Paragraph("TU PLAN NUTRICIONAL", estilos["titulo"]))
    E.append(Paragraph(f"{athlete.nombre.upper()} · {objetivo.upper()}", estilos["subtitulo"]))
    E.append(HRFlowable(width="100%", thickness=2, color=C_ACENTO_AMARILLO, spaceAfter=10))

    # Macros
    E.append(Paragraph("MACRONUTRIENTES DIARIOS", estilos["seccion"]))
    macros_data = [
        ["Macro", "Gramos", "%", "Equivalente Práctico"],
        ["Proteínas", f"{macros.prot_g}g", f"{macros.prot_p}%", f"≈ {macros.prot_g // 25} porciones de 25g"],
        ["Carbohidratos", f"{macros.carb_g}g", f"{macros.carb_p}%", f"≈ {macros.carb_g // 50} porciones de 50g"],
        ["Grasas", f"{macros.gras_g}g", f"{macros.gras_p}%", f"≈ {macros.gras_g // 15} porciones de 15g"],
    ]
    t_macros = Table(macros_data, colWidths=[1.5 * inch, 1.0 * inch, 0.8 * inch, 3.3 * inch])
    t_macros.setStyle(estilo_tabla)
    E.append(t_macros)
    E.append(Spacer(1, 0.2 * inch))

    # Guía de compras desde el plan nutricional
    E.append(Paragraph("GUÍA DE COMPRAS SEMANAL", estilos["seccion"]))
    guia_headers = ["Categoría", "Alimentos", "Frecuencia"]
    guia_rows = [guia_headers] + [
        [item.get("categoría", ""), item.get("alimentos", ""), item.get("frecuencia", "")]
        for item in nutricion.guia_compras
    ]
    t_guia = Table(guia_rows, colWidths=[1.8 * inch, 3.0 * inch, 1.8 * inch])
    t_guia.setStyle(estilo_tabla)
    E.append(t_guia)
    E.append(Spacer(1, 0.2 * inch))

    # Reglas de oro
    E.append(Paragraph("REGLAS DE ORO", estilos["seccion"]))
    for i, regla in enumerate(nutricion.reglas_oro, 1):
        E.append(Paragraph(f"{i}. {regla.upper()}", estilos["body"]))
        E.append(Spacer(1, 0.05 * inch))

    # Estrategia principal
    E.append(Spacer(1, 0.15 * inch))
    E.append(Paragraph("ESTRATEGIA NUTRICIONAL", estilos["seccion"]))
    E.append(Paragraph(nutricion.estrategia_principal, estilos["body"]))

    # Pie de página
    E.append(Spacer(1, 0.3 * inch))
    E.append(HRFlowable(width="100%", thickness=1, color=C_ACENTO_ROJO, spaceAfter=6))
    E.append(Paragraph(
        "RUTINATOR NUTRITION · EDICIÓN EDITORIAL · CONSULTA SIEMPRE A TU NUTRICIONISTA",
        estilos["footer"],
    ))

    doc.build(E)
    buffer.seek(0)
    return buffer


generar_revista_nutricional = generar_revista_nutricional_sync
