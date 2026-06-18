"""
test_extraccion.py

Set de pruebas automatizadas que valida la extracción contra resultados
esperados conocidos, tal como pide la Fase 5 del documento de pasantía
("preparar un set de PDF de prueba con su resultado esperado para
validar cambios futuros").

Uso:
    python -m pytest tests/test_extraccion.py -v

o, sin pytest instalado, simplemente:
    python tests/test_extraccion.py
"""

import sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

import pdfplumber
from extractor_encabezado import extraer_encabezado
from extractor_detalle import extraer_detalle


# ---------------------------------------------------------------------------
# Caso 1: Nota de Crédito 800001168 (caso "feliz", todos los campos presentes)
# ---------------------------------------------------------------------------
RUTA_PDF_OK = BASE / "muestras" / "800001168.pdf"

ENCABEZADO_ESPERADO_OK = {
    "ncf": "E340000000070",
    "ncf_modificado": "E310000000181",
    "numero_documento": "800001168",
    "rnc_cliente": "101019921",
    "cliente": "CENTRO CUESTA NACIONAL",
    "tipo_documento": "NOTA DE CREDITO",
    "indicador_bien_servicio": 1,
    "total": 166881.78,
}

DETALLE_ESPERADO_OK = [
    {"descripcion": "RELIQ CONTRATO POTENCIA 2025", "monto": 131453.24},
    {"descripcion": "RELIQ CONTRATO DC 2025", "monto": 27945.75},
    {"descripcion": "RELIQ CONTRATO SIE 2025", "monto": 5612.09},
    {"descripcion": "RELIQ CONTRATO CNE 2025", "monto": 1870.70},
]


def _leer_pdf(ruta_pdf: Path):
    with pdfplumber.open(ruta_pdf) as pdf:
        page = pdf.pages[0]
        return page.extract_text(), page.extract_words()


def test_encabezado_caso_feliz():
    """Verifica que todos los campos clave del encabezado se extraigan
    correctamente y con el tipo de dato esperado."""
    texto, _ = _leer_pdf(RUTA_PDF_OK)
    encabezado = extraer_encabezado(texto)

    for campo, valor_esperado in ENCABEZADO_ESPERADO_OK.items():
        assert encabezado.get(campo) == valor_esperado, (
            f"Campo '{campo}': esperado {valor_esperado!r}, "
            f"obtenido {encabezado.get(campo)!r}"
        )

    # Tipos de dato correctos (requisito explícito del documento de
    # pasantía: fechas y números nunca como texto)
    assert isinstance(encabezado["fecha_documento"], datetime)
    assert isinstance(encabezado["fecha_vencimiento"], datetime)
    assert isinstance(encabezado["total"], float)
    assert isinstance(encabezado["indicador_bien_servicio"], int)

    print("OK - test_encabezado_caso_feliz")


def test_detalle_caso_feliz():
    """Verifica que las 4 líneas de detalle se extraigan con la
    descripción y el monto correctos."""
    texto, palabras = _leer_pdf(RUTA_PDF_OK)
    encabezado = extraer_encabezado(texto)
    detalle = extraer_detalle(palabras, numero_documento=encabezado["numero_documento"])

    assert len(detalle) == len(DETALLE_ESPERADO_OK), (
        f"Se esperaban {len(DETALLE_ESPERADO_OK)} líneas, se obtuvieron {len(detalle)}"
    )

    for obtenido, esperado in zip(detalle, DETALLE_ESPERADO_OK):
        assert obtenido["descripcion"] == esperado["descripcion"]
        assert abs(obtenido["monto"] - esperado["monto"]) < 0.01
        assert isinstance(obtenido["monto"], float)

    print("OK - test_detalle_caso_feliz")


def test_cuadre_encabezado_vs_detalle():
    """Verifica que la suma de las líneas de detalle coincida con el
    total declarado en el encabezado (control de cuadre)."""
    texto, palabras = _leer_pdf(RUTA_PDF_OK)
    encabezado = extraer_encabezado(texto)
    detalle = extraer_detalle(palabras, numero_documento=encabezado["numero_documento"])

    suma_detalle = sum(linea["monto"] for linea in detalle)
    assert abs(encabezado["total"] - suma_detalle) < 0.01, (
        f"No cuadra: total encabezado={encabezado['total']}, suma detalle={suma_detalle}"
    )

    print("OK - test_cuadre_encabezado_vs_detalle")


def test_robustez_ante_campos_faltantes():
    """Verifica que el extractor de encabezado NO lance una excepción
    cuando recibe texto sin los campos esperados (caso de robustez,
    equivalente al PDF de prueba 'Nota_Credito_Prueba.pdf'). Los campos
    no encontrados deben quedar como None, no provocar un error."""
    texto_incompleto = "Este es un documento sin ningún campo reconocible."

    encabezado = extraer_encabezado(texto_incompleto)  # no debe lanzar excepción

    assert encabezado["ncf"] is None
    assert encabezado["numero_documento"] is None
    assert encabezado["fecha_documento"] is None
    assert encabezado["tipo_documento"] == "DESCONOCIDO"

    print("OK - test_robustez_ante_campos_faltantes")


def test_robustez_detalle_sin_tabla():
    """Verifica que extraer_detalle devuelva una lista vacía (no una
    excepción) cuando no hay tabla de Concepto/Total RD$ reconocible."""
    palabras_vacias = []
    detalle = extraer_detalle(palabras_vacias, numero_documento="000")
    assert detalle == []

    print("OK - test_robustez_detalle_sin_tabla")


if __name__ == "__main__":
    # Permite correr el archivo directamente con `python tests/test_extraccion.py`
    # sin necesidad de tener pytest instalado.
    funciones_test = [
        test_encabezado_caso_feliz,
        test_detalle_caso_feliz,
        test_cuadre_encabezado_vs_detalle,
        test_robustez_ante_campos_faltantes,
        test_robustez_detalle_sin_tabla,
    ]

    fallos = 0
    for funcion in funciones_test:
        try:
            funcion()
        except AssertionError as error:
            fallos += 1
            print(f"FALLO - {funcion.__name__}: {error}")

    print()
    if fallos == 0:
        print(f"Todos los {len(funciones_test)} tests pasaron correctamente.")
    else:
        print(f"{fallos} de {len(funciones_test)} tests fallaron.")
        sys.exit(1)
