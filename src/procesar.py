"""
procesar.py

Script principal: procesa por lotes todos los PDF de una carpeta y genera
un Excel consolidado, registrando en un log qué documentos se procesaron
bien y cuáles fallaron (y por qué).
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

import pdfplumber

from extractor_encabezado import extraer_encabezado
from extractor_detalle import extraer_detalle
from generador_excel import generar_excel, obtener_documentos_existentes


def configurar_log(ruta_log: Path) -> logging.Logger:
    ruta_log.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("egehid_pdf2excel")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    manejador_archivo = logging.FileHandler(ruta_log, mode="w", encoding="utf-8")
    manejador_archivo.setFormatter(formato)
    logger.addHandler(manejador_archivo)

    manejador_consola = logging.StreamHandler(sys.stdout)
    manejador_consola.setFormatter(formato)
    logger.addHandler(manejador_consola)

    return logger


def procesar_pdf(ruta_pdf: Path, logger: logging.Logger) -> dict:
    """Procesa un PDF y determina si es válido o no."""
    with pdfplumber.open(ruta_pdf) as pdf:
        if len(pdf.pages) == 0:
            raise ValueError("El PDF no contiene páginas")

        page = pdf.pages[0]
        texto = page.extract_text()
        palabras = page.extract_words()

    if not texto:
        raise ValueError("No se pudo extraer texto (PDF escaneado o imagen)")

    encabezado = extraer_encabezado(texto)

    valido = True

    campos_clave = ["ncf", "numero_documento", "fecha_documento"]
    faltantes = [c for c in campos_clave if encabezado.get(c) is None]

    if faltantes:
        logger.warning(
            f"❌ {ruta_pdf.name}: faltan campos clave: {', '.join(faltantes)}"
        )
        valido = False

    detalle = extraer_detalle(
        palabras,
        numero_documento=encabezado.get("numero_documento")
    )

    if not detalle:
        logger.warning(f"❌ {ruta_pdf.name}: no se encontraron líneas de detalle")
        valido = False

    total_encabezado = encabezado.get("total")
    if total_encabezado is not None and detalle:
        suma_detalle = sum((l.get("monto") or 0) for l in detalle)
        if abs(total_encabezado - suma_detalle) >= 0.01:
            logger.warning(
                f"{ruta_pdf.name}: NO CUADRA. "
                f"Total encabezado={total_encabezado} vs suma detalle={suma_detalle}"
            )
            valido = False

    return {
        "encabezado": encabezado,
        "detalle": detalle,
        "ruta_pdf": ruta_pdf,
        "valido": valido
    }


def mover_a_procesados(documentos: list, carpeta_procesados: Path, logger: logging.Logger) -> None:
    """Mueve solo documentos válidos a procesados."""
    carpeta_procesados.mkdir(parents=True, exist_ok=True)

    for documento in documentos:
        ruta_pdf = documento.get("ruta_pdf")
        if ruta_pdf is None or not ruta_pdf.exists():
            continue

        destino = carpeta_procesados / ruta_pdf.name
        contador = 1

        while destino.exists():
            destino = carpeta_procesados / f"{ruta_pdf.stem}_{contador}{ruta_pdf.suffix}"
            contador += 1

        try:
            shutil.move(str(ruta_pdf), str(destino))
            logger.info(f"{ruta_pdf.name}: movido a {carpeta_procesados}")
        except OSError as error:
            logger.error(f"{ruta_pdf.name}: error al mover - {error}")


def filtrar_duplicados(documentos: list, ruta_excel: str, logger: logging.Logger) -> list:
    vistos = set(obtener_documentos_existentes(ruta_excel))

    filtrados = []

    for documento in sorted(documentos, key=lambda d: d["ruta_pdf"].name):
        numero = documento["encabezado"].get("numero_documento")
        nombre_pdf = documento["ruta_pdf"].name

        if numero is not None and numero in vistos:
            logger.error(
                f"{nombre_pdf}: DUPLICADO - documento {numero} ya existe"
            )
            continue

        if numero is not None:
            vistos.add(numero)

        filtrados.append(documento)

    return filtrados


def procesar_carpeta(carpeta: Path, logger: logging.Logger) -> list:
    archivos_pdf = sorted(carpeta.glob("*.pdf"))

    if not archivos_pdf:
        logger.warning(f"No hay PDFs en {carpeta}")
        return []

    documentos = []
    ok = 0
    fail = 0

    for ruta_pdf in archivos_pdf:
        try:
            doc = procesar_pdf(ruta_pdf, logger)
            documentos.append(doc)
            logger.info(f"{ruta_pdf.name}: procesado")
            ok += 1
        except Exception as e:
            logger.error(f"{ruta_pdf.name}: FALLÓ - {e}")
            fail += 1

    logger.info(f"Resumen: {ok} OK, {fail} fallidos")
    return documentos


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--carpeta", default="muestras")
    parser.add_argument("--salida", default="salida/resultado.xlsx")
    parser.add_argument("--por-archivo", action="store_true")
    parser.add_argument("--log", default="logs/procesamiento.log")
    parser.add_argument("--carpeta-procesados", default="procesados")
    parser.add_argument("--no-mover", action="store_true")

    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    logger = configurar_log(Path(args.log))

    if not carpeta.exists():
        logger.error("La carpeta no existe")
        sys.exit(1)

    logger.info("Iniciando proceso...")

    documentos = procesar_carpeta(carpeta, logger)

    if not documentos:
        logger.warning("No hay documentos procesados")
        sys.exit(1)

    # 🔥 separar válidos e inválidos
    documentos_validos = [d for d in documentos if d.get("valido")]
    documentos_invalidos = [d for d in documentos if not d.get("valido")]

    logger.info(f"Válidos: {len(documentos_validos)} | Inválidos: {len(documentos_invalidos)}")

    if args.por_archivo:
        carpeta_salida = Path(args.salida)
        carpeta_salida.mkdir(parents=True, exist_ok=True)

        for doc in documentos_validos:
            numero = doc["encabezado"].get("numero_documento") or "sin_numero"
            ruta_excel = carpeta_salida / f"{numero}.xlsx"

            filtrados = filtrar_duplicados([doc], str(ruta_excel), logger)

            if filtrados:
                generar_excel(filtrados, str(ruta_excel))
                logger.info(f"Excel generado: {ruta_excel}")

    else:
        ruta_salida = Path(args.salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        filtrados = filtrar_duplicados(documentos_validos, str(ruta_salida), logger)

        if not filtrados:
            logger.warning("No hay datos válidos para Excel")
            sys.exit(1)

        generar_excel(filtrados, str(ruta_salida))
        logger.info(f"Excel generado: {ruta_salida}")

    # 🔥 SOLO mover válidos
    if not args.no_mover:
        mover_a_procesados(
            documentos_validos,
            Path(args.carpeta_procesados),
            logger
        )


if __name__ == "__main__":
    main()
