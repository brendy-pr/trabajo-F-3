"""
Exportacion de reportes del almacen a documentos PDF.

Este modulo transforma DataFrames de Pandas en PDF formales usando ReportLab.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


COLOR_ENCABEZADO = colors.HexColor("#1F2937")
COLOR_FILA_PAR = colors.HexColor("#F8FAFC")
COLOR_FILA_IMPAR = colors.HexColor("#E5E7EB")
COLOR_BORDE = colors.HexColor("#CBD5E1")
COLOR_TEXTO = colors.HexColor("#111827")


def _texto_seguro(valor: Any) -> str:
    """
    Convierte valores del DataFrame en texto seguro para Paragraph.
    """
    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass

    if isinstance(valor, pd.Timestamp):
        texto = valor.strftime("%Y-%m-%d %H:%M:%S")
    else:
        texto = str(valor)

    return escape(texto).replace("\n", "<br/>")


def _crear_estilos() -> Dict[str, ParagraphStyle]:
    estilos_base = getSampleStyleSheet()

    return {
        "titulo": ParagraphStyle(
            "TituloReporte",
            parent=estilos_base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=COLOR_ENCABEZADO,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloReporte",
            parent=estilos_base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
        ),
        "encabezado_tabla": ParagraphStyle(
            "EncabezadoTabla",
            parent=estilos_base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "celda": ParagraphStyle(
            "CeldaTabla",
            parent=estilos_base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_TEXTO,
            alignment=TA_LEFT,
        ),
        "mensaje": ParagraphStyle(
            "MensajeVacio",
            parent=estilos_base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#475569"),
        ),
    }


def _calcular_anchos_columnas(df_datos: pd.DataFrame, ancho_disponible: float) -> List[float]:
    total_columnas = max(1, len(df_datos.columns))
    ancho_base = ancho_disponible / total_columnas
    return [ancho_base] * total_columnas


def _crear_tabla(df_datos: pd.DataFrame, ancho_disponible: float) -> Table:
    estilos = _crear_estilos()
    encabezados = [
        Paragraph(_texto_seguro(columna), estilos["encabezado_tabla"])
        for columna in df_datos.columns
    ]

    filas = [encabezados]
    for _, fila in df_datos.iterrows():
        filas.append(
            [Paragraph(_texto_seguro(valor), estilos["celda"]) for valor in fila.tolist()]
        )

    tabla = Table(
        filas,
        colWidths=_calcular_anchos_columnas(df_datos, ancho_disponible),
        repeatRows=1,
        splitByRow=True,
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ENCABEZADO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_FILA_PAR, COLOR_FILA_IMPAR]),
                ("GRID", (0, 0), (-1, -1), 0.35, COLOR_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabla


def _crear_encabezado_pie(titulo_reporte: str, fecha_generacion: str):
    def dibujar(canvas, documento):
        canvas.saveState()
        ancho_pagina, alto_pagina = documento.pagesize

        y_encabezado = alto_pagina - 1.2 * cm
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(COLOR_ENCABEZADO)
        canvas.drawString(documento.leftMargin, y_encabezado, titulo_reporte)

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawRightString(
            ancho_pagina - documento.rightMargin,
            y_encabezado,
            f"Fecha: {fecha_generacion}",
        )

        canvas.setStrokeColor(COLOR_BORDE)
        canvas.line(
            documento.leftMargin,
            y_encabezado - 0.25 * cm,
            ancho_pagina - documento.rightMargin,
            y_encabezado - 0.25 * cm,
        )

        y_pie = 1.1 * cm
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.line(
            documento.leftMargin,
            y_pie + 0.35 * cm,
            ancho_pagina - documento.rightMargin,
            y_pie + 0.35 * cm,
        )
        canvas.drawCentredString(
            ancho_pagina / 2,
            y_pie,
            f"Pagina {documento.page}",
        )
        canvas.restoreState()

    return dibujar


def exportar_a_pdf(
    nombre_archivo: str,
    titulo_reporte: str,
    df_datos: pd.DataFrame,
) -> str:
    """
    Exporta un DataFrame a un PDF formal con encabezado, tabla y pie de pagina.
    """
    if not isinstance(df_datos, pd.DataFrame):
        raise TypeError("df_datos debe ser un DataFrame de Pandas.")

    ruta_pdf = Path(nombre_archivo)
    if ruta_pdf.suffix.lower() != ".pdf":
        ruta_pdf = ruta_pdf.with_suffix(".pdf")

    if ruta_pdf.parent != Path(""):
        ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    paginas = landscape(A4) if len(df_datos.columns) > 5 else A4

    documento = SimpleDocTemplate(
        str(ruta_pdf),
        pagesize=paginas,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.0 * cm,
        title=titulo_reporte,
        author="Sistema inteligente de gestion de almacen",
    )

    estilos = _crear_estilos()
    contenido = [
        Paragraph(escape(titulo_reporte), estilos["titulo"]),
        Paragraph(f"Generado el {fecha_generacion}", estilos["subtitulo"]),
        Spacer(1, 0.35 * cm),
    ]

    if df_datos.empty:
        contenido.append(
            Paragraph("No hay datos disponibles para este reporte.", estilos["mensaje"])
        )
    else:
        contenido.append(_crear_tabla(df_datos.copy(), documento.width))

    encabezado_pie = _crear_encabezado_pie(titulo_reporte, fecha_generacion)
    documento.build(
        contenido,
        onFirstPage=encabezado_pie,
        onLaterPages=encabezado_pie,
    )

    return str(ruta_pdf)


