"""
extractor_encabezado.py

Extrae los campos de ENCABEZADO de una Nota de Crédito / Factura EGEHID
a partir del texto plano del PDF.

Diseño:
- La extracción se basa en ANCLAS DE TEXTO (regex sobre etiquetas conocidas:
  "NCF :", "Cliente :", etc.), NO en coordenadas absolutas fijas.
- Esto hace el extractor tolerante a pequeños desplazamientos verticales/
  horizontales de los campos entre un PDF y otro, siempre que las etiquetas
  de texto se mantengan iguales.
- Si en el futuro cambia el formato (otra etiqueta, otro orden), solo hay
  que ajustar el diccionario PATRONES, sin tocar la lógica de extracción.
"""

import re
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Patrones de extracción
# ---------------------------------------------------------------------------
PATRONES = {
    "fecha_documento": r"Fecha\s+de\s+Factura\s*:\s*([\d.]+)",
    "ncf": r"NCF\s*:\s*([A-Z0-9]+)",
    "ncf_modificado": r"NCF\s+Modificado\s*:\s*([A-Z0-9]+)",
    "rnc_cliente": r"RNC\s*:\s*(\d[\d-]*)",
    "cliente": r"Cliente\s*:\s*(.+?)(?:\s{2,}|\s+Fecha\s+Vcto|$)",
    "numero_documento": r"Nota\s+de\s+Cr[eé]dito\s+No\.\s*:\s*(\d+)",
    "fecha_vencimiento": r"Fecha\s+Vcto\.\s+Factura\s*:\s*([\d.]+)",
    "total": r"Total\s+en\s+RD\$\s+([\d,]+\.\d{2})",
}


TIPOS_DOCUMENTO = {
    "NOTA DE CREDITO": r"NOTA\s+DE\s+CREDITO",
    "NOTA DE DEBITO": r"NOTA\s+DE\s+DEBITO",
    "FACTURA": r"\bFACTURA\b(?!\s+DE\s+CREDITO)",
}


INDICADOR_BIEN_SERVICIO = 1


def _convertir_fecha(valor: Optional[str]) -> Optional[datetime]:
    if not valor:
        return None
    valor = valor.strip()
    for formato in (
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%-d.%-m.%Y",   # sin cero: 2.6.2026
        "%-d/%-m/%Y",   # sin cero: 2/6/2026
        "%-d-%-m-%Y",   # sin cero: 2-6-2026
    ):
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            pass
    return None


def _convertir_monto(valor: Optional[str]) -> Optional[float]:
    if not valor:
        return None
    valor = valor.strip()
    # Formato europeo: 166.881,78 → convertir a 166881.78
    if "," in valor and "." in valor:
        if valor.index(",") > valor.index("."):
            # El punto es separador de miles, la coma es decimal
            valor = valor.replace(".", "").replace(",", ".")
        else:
            # El punto es decimal (formato normal), quitar comas
            valor = valor.replace(",", "")
    elif "," in valor:
        # Solo coma — asumir decimal europeo
        valor = valor.replace(",", ".")
    else:
        valor = valor.replace(",", "")
    try:
        return float(valor)
    except ValueError:
        return None


def detectar_tipo_documento(texto: str) -> str:
    """Detecta el tipo de documento."""

    for tipo, patron in TIPOS_DOCUMENTO.items():

        if re.search(patron, texto, re.IGNORECASE):

            return tipo

    return "DESCONOCIDO"


def extraer_observaciones(texto: str) -> Optional[str]:
    """
    Extrae el bloque de observaciones del documento.

    Captura todo el texto que aparece debajo de "OBSERVACIONES"
    hasta antes de la firma o del final del documento.
    """

    patron = (
        r"OBSERVACIONES\s*:?\s*"
        r"(.*?)"
        r"(?=_{3,}|Elaborado\s+Por|Revisado\s+Por|Aprobado\s+Por|Licda\.|Lic\.|$)"
    )

    coincidencia = re.search(
        patron,
        texto,
        re.IGNORECASE | re.DOTALL,
    )

    if not coincidencia:
        return None

    observaciones = coincidencia.group(1)

    # Reemplazar múltiples espacios y saltos de línea por uno solo
    observaciones = re.sub(r"\s+", " ", observaciones)

    observaciones = observaciones.strip()

    return observaciones if observaciones else None


def extraer_encabezado(texto: str) -> dict:
    """
    Extrae los datos del encabezado del PDF.

    Devuelve un diccionario con los datos convertidos a sus
    tipos correspondientes.
    """

    encabezado = {}

    for campo, patron in PATRONES.items():

        coincidencia = re.search(
            patron,
            texto,
            re.IGNORECASE | re.MULTILINE,
        )

        if coincidencia:

            valor = coincidencia.group(1).strip()

            encabezado[campo] = valor if valor else None

        else:

            encabezado[campo] = None

    # Conversión de tipos

    encabezado["fecha_documento"] = _convertir_fecha(
        encabezado["fecha_documento"]
    )

    encabezado["fecha_vencimiento"] = _convertir_fecha(
        encabezado["fecha_vencimiento"]
    )

    encabezado["total"] = _convertir_monto(
        encabezado["total"]
    )

    # Campos calculados

    encabezado["tipo_documento"] = detectar_tipo_documento(texto)

    encabezado["indicador_bien_servicio"] = INDICADOR_BIEN_SERVICIO

    # NUEVO CAMPO

    encabezado["observaciones"] = extraer_observaciones(texto)

    return encabezado


if __name__ == "__main__":

    import pdfplumber

    with pdfplumber.open("../muestras/800001168.pdf") as pdf:

        texto_pdf = pdf.pages[0].extract_text()

    resultado = extraer_encabezado(texto_pdf)

    for clave, valor in resultado.items():

        print(f"{clave:25}: {valor}")