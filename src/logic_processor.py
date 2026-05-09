import io
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# --- PALETA DE COLORES ---
C_PRIMARIO = colors.HexColor("#0F172A")
C_SECUNDARIO = colors.HexColor("#2563EB")
C_TEXTO = colors.HexColor("#334155")
C_FONDO_TABLA = colors.HexColor("#F8FAFC")
C_FONDO_CLARO = colors.HexColor("#E2E8F0")

C_DARK_BG = colors.HexColor("#0A0A0A")
C_ACCENT_GREEN = colors.HexColor("#84CC16")
C_ACCENT_BLUE = colors.HexColor("#3B82F6")
C_WHITE = colors.HexColor("#FFFFFF")
C_GRAY_TEXT = colors.HexColor("#94A3B8")

def crear_tabla_semanal(ejercicios_filtrados, semana_num):
    factor_peso = 1.0
    if semana_num in [2, 3]: factor_peso = 1.05
    elif semana_num == 4: factor_peso = 0.80
    
    datos = [['Ejercicio', 'Series x Reps', 'Peso (kg)', 'Objetivo']]
    for _, row in ejercicios_filtrados.iterrows():
        peso_base = 50.0 
        peso_ajustado = round(peso_base * factor_peso, 1)
        datos.append([row['Nombre_ES'], "3 x 10-12", f"{peso_ajustado}kg", "Técnica"])
    
    tabla = Table(datos, colWidths=[2*inch, 1*inch, 1.2*inch, 2.5*inch])
    estilo = [
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARIO),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, C_FONDO_CLARO),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]
    tabla.setStyle(TableStyle(estilo))
    return tabla

def generar_pdf_rutina(datos_usuario):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = []
    
    elementos.append(Paragraph(f"RUTINA DE ENTRENAMIENTO: {datos_usuario['atleta']}", styles['Heading1']))
    elementos.append(Spacer(1, 0.2*inch))
    
    # Simulación de datos (En producción cargar desde CSV)
    data_ejercicios = {
        'Nombre_ES': ['Sentadilla Copa', 'Press Banca', 'Remo con Mancuerna'],
        'Patron': ['Sentadilla', 'Empuje', 'Tracción']
    }
    df_ejercicios = pd.DataFrame(data_ejercicios)
    
    for i in range(1, 5):
        tipo = "Carga" if i < 4 else "Descarga"
        elementos.append(Paragraph(f"Semana {i} ({tipo})", styles['Heading3']))
        elementos.append(crear_tabla_semanal(df_ejercicios, i))
        elementos.append(Spacer(1, 0.2*inch))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

def generar_revista_nutricional(datos_usuario):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    h1 = ParagraphStyle('MagH1', parent=styles['Heading1'], fontSize=24, textColor=C_PRIMARIO)
    body = ParagraphStyle('MagBody', parent=styles['Normal'], fontSize=11, textColor=C_TEXTO)
    
    elementos = []
    elementos.append(Paragraph("COME COMO ENTRENAS - EDICIÓN CHILE", h1))
    elementos.append(Spacer(1, 0.2*inch))
    elementos.append(Paragraph("<b>Sección Feria Libre:</b> Maqui, Betarraga y Espinaca.", body))
    elementos.append(Paragraph("<b>Proteína del Mar:</b> Jurel y Sardinas (Omega-3).", body))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer
