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
- Soporte para PDF de varias páginas: procesar.py concatena las palabras
  de todas las páginas ajustando el offset vertical, de modo que esta
  función no necesita saber cuántas páginas tiene el documento.
"""

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
    `page.extract_words()` de pdfplumber, con offsets verticales ya
    aplicados para documentos de varias páginas) y devuelve una lista
    de diccionarios, uno por cada línea de detalle:
        {"numero_documento": ..., "descripcion": ..., "monto": ...}

    Si no se encuentra la cabecera de la tabla ("Concepto" / "Total RD$"),
    devuelve una lista vacía en lugar de lanzar una excepción, para que
    el procesamiento por lotes pueda registrar el error en el log y
    continuar con el resto de los documentos.

    Soporte multipágina: procesar.py concatena las palabras de todas las
    páginas con offsets verticales acumulados antes de llamar a esta
    función, por lo que el detalle se extrae correctamente aunque la
    tabla esté en la segunda página o posterior.
    """
    palabra_concepto = next(
    (w for w in palabras if w["text"].strip().lower().replace(":", "") == "concepto"), None
)
    palabra_total_rd = next(
        (w for w in palabras if "RD$" in w["text"]), None
    )

    if palabra_concepto is None or palabra_total_rd is None:
        return []

    top_cabecera = palabra_concepto["top"]
    x_inicio_monto = palabra_total_rd["x0"] - 15  # margen de tolerancia

    # "Total en RD$" marca el fin de la tabla de detalle.
    # Se busca la primera palabra "total" que aparezca DESPUÉS de la cabecera.
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
            # Línea incompleta o no relacionada con la tabla; se omite.
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
    import sys
    import pdfplumber

    ruta = sys.argv[1] if len(sys.argv) > 1 else "../muestras/800001168.pdf"

    palabras_todas = []
    offset_vertical = 0.0

    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages:
            palabras_pagina = page.extract_words()
            for palabra in palabras_pagina:
                copia = dict(palabra)
                copia["top"] = copia["top"] + offset_vertical
                palabras_todas.append(copia)
            if palabras_pagina:
                offset_vertical += max(w["bottom"] for w in palabras_pagina) + 10

    resultado = extraer_detalle(palabras_todas, numero_documento="800001168")
    for fila in resultado:
        print(fila)
