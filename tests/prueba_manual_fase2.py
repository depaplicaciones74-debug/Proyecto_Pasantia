
"""
prueba_fase2.py

Prueba la extracción de un único PDF:
1. Extrae el encabezado como diccionario.
2. Extrae el detalle como lista de diccionarios.
3. Verifica que fechas y montos tengan su tipo correcto.
4. Comprueba que los campos faltantes no provoquen errores.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

import pdfplumber

from extractor_encabezado import extraer_encabezado
from extractor_detalle import extraer_detalle

RUTA_PDF = BASE / "muestras" / "800001168.pdf"

with pdfplumber.open(RUTA_PDF) as pdf:
    pagina = pdf.pages[0]
    texto = pagina.extract_text()
    palabras = pagina.extract_words()

# ===========================
# ENCABEZADO
# ===========================

encabezado = extraer_encabezado(texto)

print("=" * 50)
print("ENCABEZADO")
print("=" * 50)

for clave, valor in encabezado.items():
    print(f"{clave:25}: {valor} ({type(valor).__name__})")

# ===========================
# DETALLE
# ===========================

detalle = extraer_detalle(
    palabras,
    numero_documento=encabezado.get("numero_documento")
)

print("\n")
print("=" * 50)
print("DETALLE")
print("=" * 50)

for fila in detalle:
    print(fila)

# ===========================
# VALIDACIONES
# ===========================

print("\n")
print("=" * 50)
print("VALIDACIONES")
print("=" * 50)

print(
    "Fecha documento es datetime:",
    encabezado["fecha_documento"].__class__.__name__
)

print(
    "Fecha vencimiento es datetime:",
    encabezado["fecha_vencimiento"].__class__.__name__
)

print(
    "Total es float:",
    encabezado["total"].__class__.__name__
)

if detalle:

    print(
        "Monto detalle es float:",
        detalle[0]["monto"].__class__.__name__
    )

print("\nCampos faltantes:")

for campo, valor in encabezado.items():

    if valor is None:

        print(f"{campo}: None (manejado correctamente)")