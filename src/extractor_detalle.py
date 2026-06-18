"""
extractor_detalle.py

Extrae las líneas de DETALLE (Concepto / Total RD$) de una Nota de
Crédito / Factura EGEHID.

Diseño:
- A diferencia del encabezado (que se extrae con regex sobre texto plano),
  el detalle se extrae usando las PALABRAS CON COORDENADAS (x0, top, etc.)
  que entrega pdfplumber, porque el texto plano mezcla la descripción y el
  monto sin un separador fiable.
- Se ubica la fila de encabezado de la tabla ("Concepto" / "Total RD$")
  para conocer en qué posición vertical empieza la tabla y en qué columna
  X arranca cada campo. Luego se agrupan las palabras restantes por línea
  (mismo "top") y se separan en descripción (columna izquierda) y monto
  (columna derecha) según esa posición X de referencia.
- Esto es más robusto que coordenadas absolutas fijas: si el documento se
  desplaza unos puntos verticalmente, igual funciona, porque la posición
  se calcula de forma relativa a las cabeceras "Concepto" y "Total RD$".
"""

import re
from typing import Optional


def _convertir_monto(valor: str) -> Optional[float]:
    """Convierte montos con formato '131,453.24' a float."""
    limpio = valor.strip().replace(",", "")
    try:
        return float(limpio)
    except ValueError:
        return None


def _agrupar_por_linea(palabras: list, tolerancia: float = 2.0) -> list:
    """Agrupa una lista de palabras (dicts de pdfplumber) en líneas,
    según su coordenada vertical 'top', permitiendo una pequeña
    tolerancia para diferencias de redondeo entre palabras de la
    misma línea."""
    lineas = []
    for palabra in sorted(palabras, key=lambda w: (w["top"], w["x0"])):
        ubicada = False
        for linea in lineas:
            if abs(linea[0]["top"] - palabra["top"]) <= tolerancia:
                linea.append(palabra)
                ubicada = True
                break
        if not ubicada:
            lineas.append([palabra])
    return lineas


def extraer_detalle(palabras: list, numero_documento: Optional[str] = None) -> list:
    """
    Recibe la lista de palabras con coordenadas (salida de
    `page.extract_words()` de pdfplumber) y devuelve una lista de
    diccionarios, uno por cada línea de detalle:
        {"numero_documento": ..., "descripcion": ..., "monto": ...}

    Si no se encuentra la cabecera de la tabla ("Concepto" / "Total RD$"),
    devuelve una lista vacía en lugar de lanzar una excepción, para que
    el procesamiento por lotes pueda registrar el error en el log y
    continuar con el resto de los documentos.
    """
    palabra_concepto = next(
        (w for w in palabras if w["text"].strip().lower() == "concepto"), None
    )
    palabra_total_rd = next(
        (w for w in palabras if "RD$" in w["text"]), None
    )

    if palabra_concepto is None or palabra_total_rd is None:
        return []

    top_cabecera = palabra_concepto["top"]
    x_inicio_monto = palabra_total_rd["x0"] - 15  # margen de tolerancia

    # "Total en RD$" marca el fin de la tabla de detalle.
    palabra_fin = next(
        (
            w
            for w in palabras
            if w["text"].strip().lower() == "total" and w["top"] > top_cabecera
        ),
        None,
    )
    top_fin = palabra_fin["top"] if palabra_fin else float("inf")

    # Palabras que están debajo de la cabecera y antes de la fila de "Total"
    palabras_tabla = [
        w
        for w in palabras
        if w["top"] > top_cabecera + 2 and w["top"] < top_fin
    ]

    lineas = _agrupar_por_linea(palabras_tabla)

    detalle = []
    for linea in lineas:
        palabras_desc = [w for w in linea if w["x0"] < x_inicio_monto]
        palabras_monto = [w for w in linea if w["x0"] >= x_inicio_monto]

        descripcion = " ".join(w["text"] for w in palabras_desc).strip()
        texto_monto = " ".join(w["text"] for w in palabras_monto).strip()

        if not descripcion or not texto_monto:
            # Línea incompleta o no relacionada con la tabla; se omite
            # pero se podría registrar en el log de advertencias.
            continue

        monto = _convertir_monto(texto_monto)

        detalle.append(
            {
                "numero_documento": numero_documento,
                "descripcion": descripcion,
                "monto": monto,
            }
        )

    return detalle


if __name__ == "__main__":
    import pdfplumber

    with pdfplumber.open("../muestras/800001168.pdf") as pdf:
        page = pdf.pages[0]
        palabras_pdf = page.extract_words()

    resultado = extraer_detalle(palabras_pdf, numero_documento="800001168")
    for fila in resultado:
        print(fila)
