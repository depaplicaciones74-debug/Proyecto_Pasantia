"""
procesar.py

Script principal: procesa por lotes todos los PDF de una carpeta y genera
un Excel consolidado, registrando en un log qué documentos se procesaron
bien y cuáles fallaron (y por qué).

Uso:
    python procesar.py --carpeta ./muestras --salida ./salida/resultado.xlsx
    python procesar.py --carpeta ./muestras --salida ./salida --por-archivo
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
    """Procesa un único PDF y devuelve {"encabezado":..., "detalle":...}.
    Lanza una excepción si el PDF no se puede abrir o el encabezado
    no se pudo extraer en lo absoluto, para que el llamador la capture
    y la registre en el log sin detener el resto del lote."""
    with pdfplumber.open(ruta_pdf) as pdf:
        if len(pdf.pages) == 0:
            raise ValueError("El PDF no contiene páginas")
        page = pdf.pages[0]
        texto = page.extract_text()
        palabras = page.extract_words()

    if not texto:
        raise ValueError("No se pudo extraer texto (¿PDF escaneado/imagen?)")

    encabezado = extraer_encabezado(texto)

    campos_clave = ["ncf", "numero_documento", "fecha_documento"]
    faltantes = [c for c in campos_clave if encabezado.get(c) is None]
    if faltantes:
        logger.warning(
            f"{ruta_pdf.name}: campos clave no encontrados: {', '.join(faltantes)}"
        )

    detalle = extraer_detalle(palabras, numero_documento=encabezado.get("numero_documento"))
    if not detalle:
        logger.warning(f"{ruta_pdf.name}: no se encontraron líneas de detalle")

    total_encabezado = encabezado.get("total")
    if total_encabezado is not None and detalle:
        suma_detalle = sum((l.get("monto") or 0) for l in detalle)
        if abs(total_encabezado - suma_detalle) >= 0.01:
            logger.warning(
                f"{ruta_pdf.name}: NO CUADRA. Total encabezado={total_encabezado} "
                f"vs suma detalle={suma_detalle}"
            )

    return {"encabezado": encabezado, "detalle": detalle, "ruta_pdf": ruta_pdf}


def mover_a_procesados(documentos: list, carpeta_procesados: Path, logger: logging.Logger) -> None:
    """Mueve a `carpeta_procesados` cada PDF que se procesó exitosamente
    (es decir, que llegó a incluirse en el Excel), para evitar que se
    vuelva a procesar por error en una ejecución futura.

    Si un archivo con el mismo nombre ya existe en `carpeta_procesados`
    (por ejemplo, porque se reprocesó el mismo PDF manualmente), se le
    agrega un sufijo numérico en vez de sobrescribirlo, para no perder
    ninguna copia."""
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
            logger.error(f"{ruta_pdf.name}: no se pudo mover a {carpeta_procesados} - {error}")


def filtrar_duplicados(documentos: list, ruta_excel: str, logger: logging.Logger) -> list:
    """Compara los documentos recién procesados contra los números de
    documento que ya están en el Excel acumulado (si existe), Y TAMBIÉN
    entre sí mismos dentro del mismo lote (por si dos PDF del mismo
    código llegan en la misma ejecución). El número de documento es el
    código único de la factura/nota de crédito, así que cualquier
    repetición indica que ese documento ya se había procesado antes o
    viene duplicado en la carpeta de origen.

    Los documentos duplicados se excluyen y se reportan como ERROR en
    el log (no se agregan de nuevo, para no corromper el Excel
    acumulado con datos repetidos). Si hay dos PDF con el mismo número
    de documento en el mismo lote, se conserva el primero (por orden
    alfabético de nombre de archivo) y el resto se marca como
    duplicado."""
    vistos = set(obtener_documentos_existentes(ruta_excel))

    documentos_filtrados = []
    for documento in documentos:
        numero = documento["encabezado"].get("numero_documento")
        nombre_pdf = documento.get("ruta_pdf").name if documento.get("ruta_pdf") else "?"

        if numero is not None and numero in vistos:
            logger.error(
                f"{nombre_pdf}: DUPLICADO - el documento No. {numero} ya existe "
                f"en el Excel acumulado o se repite en este mismo lote, "
                f"no se agregará de nuevo"
            )
            continue

        if numero is not None:
            vistos.add(numero)

        documentos_filtrados.append(documento)

    return documentos_filtrados


def procesar_carpeta(carpeta: Path, logger: logging.Logger) -> list:
    archivos_pdf = sorted(carpeta.glob("*.pdf"))
    if not archivos_pdf:
        logger.warning(f"No se encontraron archivos PDF en {carpeta}")
        return []

    documentos = []
    exitosos = 0
    fallidos = 0

    for ruta_pdf in archivos_pdf:
        try:
            documento = procesar_pdf(ruta_pdf, logger)
            documentos.append(documento)
            logger.info(f"{ruta_pdf.name}: procesado correctamente")
            exitosos += 1
        except Exception as error:
            logger.error(f"{ruta_pdf.name}: FALLÓ - {error}")
            fallidos += 1

    logger.info(f"Resumen: {exitosos} procesados, {fallidos} con error, de {len(archivos_pdf)} totales")
    return documentos


def main():
    parser = argparse.ArgumentParser(
        description="Procesa facturas PDF de EGEHID a Excel"
    )

    parser.add_argument(
        "--carpeta",
        default="muestras",
        help="Carpeta con los PDF a procesar"
    )

    parser.add_argument(
        "--salida",
        default="salida/resultado.xlsx",
        help="Ruta del Excel de salida (o carpeta si se usa --por-archivo)"
    )

    parser.add_argument(
        "--por-archivo",
        action="store_true",
        help="Generar un Excel por cada PDF en vez de uno consolidado"
    )

    parser.add_argument(
        "--log",
        default="logs/procesamiento.log",
        help="Ruta del archivo de log"
    )

    parser.add_argument(
        "--carpeta-procesados",
        default="procesados",
        help="Carpeta a la que se mueven los PDF ya incluidos en el Excel (por defecto 'procesados')"
    )

    parser.add_argument(
        "--no-mover",
        action="store_true",
        help="No mover los PDF procesados (se quedan en la carpeta de origen)"
    )

    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    ruta_log = Path(args.log)
    ruta_log.parent.mkdir(parents=True, exist_ok=True)

    ruta_salida = Path(args.salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    carpeta_procesados = Path(args.carpeta_procesados)
    carpeta_procesados.mkdir(parents=True, exist_ok=True)

    logger = configurar_log(ruta_log)

    logger.info(f"Iniciando procesamiento de {carpeta}")
    logger.info(f"Excel de salida: {ruta_salida}")
    logger.info(f"Log: {ruta_log}")
    logger.info(f"Procesados: {carpeta_procesados}")

    documentos = procesar_carpeta(carpeta, logger)
    documentos = procesar_carpeta(carpeta, logger)

    if not documentos:
        logger.warning("No se generó ningún Excel: no hay documentos procesados")
        sys.exit(1)

    if args.por_archivo:
        carpeta_salida = Path(args.salida)
        carpeta_salida.mkdir(parents=True, exist_ok=True)

        for documento in documentos:
            numero = documento["encabezado"].get("numero_documento") or "sin_numero"
            ruta_excel = carpeta_salida / f"{numero}.xlsx"

            documentos_filtrados = filtrar_duplicados([documento], str(ruta_excel), logger)
            if not documentos_filtrados:
                continue

            generar_excel(documentos_filtrados, str(ruta_excel))
            logger.info(f"Excel generado: {ruta_excel}")

    else:
        ruta_salida = Path(args.salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        documentos = filtrar_duplicados(documentos, str(ruta_salida), logger)
        if not documentos:
            logger.warning("Todos los documentos eran duplicados; no se actualizó el Excel")
            sys.exit(1)

        generar_excel(documentos, str(ruta_salida))
        logger.info(f"Excel consolidado generado: {ruta_salida}")

    if not args.no_mover:
        carpeta_procesados = Path(args.carpeta_procesados)
        mover_a_procesados(documentos, carpeta_procesados, logger)


if __name__ == "__main__":
    main()
