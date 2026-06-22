#!/usr/bin/env bash
set -e

# Carpeta raíz del proyecto = carpeta donde está este script
RAIZ="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo " EGEHID — Instalador del proyecto"
echo "============================================================"
echo

echo "[1/4] Creando carpetas del proyecto..."
for DIR in muestras salida logs procesados src tests; do
    if [ ! -d "$RAIZ/$DIR" ]; then
        mkdir -p "$RAIZ/$DIR"
        echo "       + $DIR"
    else
        echo "       = $DIR  (ya existe)"
    fi
done
echo

echo "[2/4] Verificando Python..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 no encontrado. Instálalo con tu gestor de paquetes."
    exit 1
fi
python3 --version
echo

echo "[3/4] Creando entorno virtual (venv)..."
if [ ! -d "$RAIZ/venv" ]; then
    python3 -m venv "$RAIZ/venv"
    echo "       Entorno virtual creado."
else
    echo "       El entorno virtual ya existe."
fi
echo

echo "[4/4] Instalando dependencias..."
"$RAIZ/venv/bin/pip" install --upgrade pip --quiet
"$RAIZ/venv/bin/pip" install -r "$RAIZ/requirements.txt"
echo

echo "============================================================"
echo " Instalación completada correctamente."
echo
echo " Para procesar PDFs, pon los archivos en:"
echo "   $RAIZ/muestras/"
echo
echo " Luego ejecuta:"
echo "   cd '$RAIZ/src'"
echo "   ../venv/bin/python procesar.py"
echo "============================================================"