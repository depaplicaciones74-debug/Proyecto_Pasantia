# -*- coding: utf-8 -*-
"""
menu.py

Interfaz interactiva de línea de comandos para la herramienta
EGEHID - Extractor PDF a Excel.

Uso:
    python menu.py          (desde la carpeta src/)

No requiere dependencias adicionales más allá de las del proyecto
(pdfplumber, openpyxl). No necesita Flask ni ningún servidor web.
Funciona en CMD y PowerShell en Windows, y en terminal en Linux/Mac.
"""

import logging
import os
import sys
import time
from pathlib import Path

# ── Colores ANSI ──────────────────────────────────────────────────────────────
# Windows 10+ soporta ANSI en CMD/PowerShell de forma nativa.
# En versiones antiguas los códigos se ignoran (el texto se ve igual, sin color).

RESET  = "\033[0m"
NEGRITA = "\033[1m"
AZUL   = "\033[94m"
CYAN   = "\033[96m"
VERDE  = "\033[92m"
AMARILLO = "\033[93m"
ROJO   = "\033[91m"
GRIS   = "\033[90m"
BLANCO = "\033[97m"

def _habilitar_colores_windows():
    """Habilita el procesamiento de códigos ANSI en la consola de Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

_habilitar_colores_windows()

# ── Helpers de presentación ───────────────────────────────────────────────────

ANCHO = 60

def limpiar():
    os.system("cls" if sys.platform == "win32" else "clear")

def linea(char="─"):
    print(GRIS + char * ANCHO + RESET)

def titulo(texto):
    print()
    linea("═")
    print(f"{NEGRITA}{AZUL}  {texto}{RESET}")
    linea("═")
    print()

def seccion(texto):
    print()
    print(f"{NEGRITA}{CYAN}  {texto}{RESET}")
    linea()

def ok(texto):
    print(f"  {VERDE}✔{RESET}  {texto}")

def warn(texto):
    print(f"  {AMARILLO}⚠{RESET}  {texto}")

def error(texto):
    print(f"  {ROJO}✖{RESET}  {texto}")

def info(texto):
    print(f"  {GRIS}·{RESET}  {texto}")

def barra_progreso(actual, total, ancho=30):
    """Dibuja una barra de progreso en la misma línea."""
    porcentaje = actual / total if total else 1
    lleno = int(ancho * porcentaje)
    barra = "█" * lleno + "░" * (ancho - lleno)
    print(f"\r  {AZUL}[{barra}]{RESET} {actual}/{total}", end="", flush=True)

def pedir_input(prompt, default=None):
    """Pide un valor al usuario. Si presiona Enter sin escribir nada,
    devuelve el valor por defecto si lo hay."""
    texto_default = f" {GRIS}[{default}]{RESET}" if default else ""
    try:
        valor = input(f"  {NEGRITA}>{RESET} {prompt}{texto_default}: ").strip()
        return valor if valor else default
    except (KeyboardInterrupt, EOFError):
        print()
        return default

def menu_opciones(opciones: list, prompt="Elige una opción") -> int:
    """Muestra un menú numerado y devuelve el índice (0-based) de la
    opción elegida. Repite hasta recibir una entrada válida."""
    for i, opcion in enumerate(opciones, start=1):
        print(f"  {AZUL}{i}{RESET}. {opcion}")
    print()
    while True:
        valor = pedir_input(prompt)
        if valor and valor.isdigit():
            idx = int(valor) - 1
            if 0 <= idx < len(opciones):
                return idx
        warn("Opción no válida, intenta de nuevo.")


# ── Cabecera de la aplicación ─────────────────────────────────────────────────

def mostrar_cabecera():
    limpiar()
    print()
    print(f"{NEGRITA}{AZUL}  ╔{'═'*50}╗")
    print(f"  ║{'EGEHID - Extractor PDF a Excel':^50}║")
    print(f"  ║{'Empresa de Generación Hidroeléctrica Dom.':^50}║")
    print(f"  ╚{'═'*50}╝{RESET}")
    print()


# ── Flujo principal ───────────────────────────────────────────────────────────

def flujo_procesar():
    """Guía al usuario paso a paso para procesar un lote de PDFs."""

    # ── Paso 1: Carpeta de entrada ─────────────────────────
    seccion("Paso 1 de 4 - Carpeta con los PDF a procesar")
    print("  Ingresa la ruta de la carpeta que contiene los archivos PDF.")
    print(f"  {GRIS}Ejemplo: C:\\Facturas\\Junio2026  o  ../muestras{RESET}")
    print()

    while True:
        carpeta_str = pedir_input("Ruta de la carpeta")
        if not carpeta_str:
            warn("Debes ingresar una ruta.")
            continue
        carpeta = Path(carpeta_str)
        if not carpeta.is_dir():
            error(f"La carpeta no existe: {carpeta_str}")
            continuar = pedir_input("¿Intentar con otra ruta? (s/n)", default="s")
            if continuar and continuar.lower() == "s":
                continue
            return
        pdfs = sorted(carpeta.glob("*.pdf"))
        if not pdfs:
            warn(f"No se encontraron archivos .pdf en: {carpeta_str}")
            continuar = pedir_input("¿Intentar con otra ruta? (s/n)", default="s")
            if continuar and continuar.lower() == "s":
                continue
            return
        ok(f"Encontrados {len(pdfs)} archivo(s) PDF")
        break

    # ── Paso 2: Archivo de salida ──────────────────────────
    seccion("Paso 2 de 4 - Archivo Excel de salida")
    print("  ¿Quieres generar un solo Excel consolidado con todas las")
    print("  facturas, o un Excel individual por cada PDF?")
    print()
    modo_idx = menu_opciones([
        "Un solo Excel consolidado (recomendado)",
        "Un Excel por cada PDF (se guardan en una carpeta)",
    ])
    por_archivo = modo_idx == 1

    print()
    if por_archivo:
        print(f"  {GRIS}Ingresa la carpeta donde se guardarán los Excel individuales.{RESET}")
        salida_default = str(carpeta.parent / "salida")
        salida_str = pedir_input("Carpeta de salida", default=salida_default)
        ruta_salida = Path(salida_str)
    else:
        salida_default = str(carpeta.parent / "salida" / "resultado.xlsx")
        salida_str = pedir_input("Ruta del Excel consolidado", default=salida_default)
        ruta_salida = Path(salida_str)

        if ruta_salida.exists():
            print()
            warn(f"El archivo ya existe: {ruta_salida.name}")
            print(f"  {GRIS}Si continúas, los nuevos documentos se AGREGARÁN al final")
            print(f"  del Excel existente (no se borrará lo que ya hay).{RESET}")
            print()
            accion_idx = menu_opciones([
                "Agregar al Excel existente (acumular)",
                "Elegir otro nombre de archivo",
                "Cancelar",
            ])
            if accion_idx == 1:
                salida_str = pedir_input("Nueva ruta del Excel")
                ruta_salida = Path(salida_str)
            elif accion_idx == 2:
                return

    # ── Paso 3: Carpeta de procesados ─────────────────────
    seccion("Paso 3 de 4 - Manejo de archivos procesados")
    print("  Después de procesar cada PDF exitosamente, ¿quieres moverlo")
    print("  a una carpeta 'procesados/' para no volver a procesarlo?")
    print()
    mover_idx = menu_opciones([
        "Sí, mover los PDF procesados a 'procesados/'",
        "No, dejar los PDF donde están",
    ])
    mover = mover_idx == 0
    carpeta_procesados = carpeta.parent / "procesados" if mover else None

    # ── Paso 4: Confirmación ───────────────────────────────
    seccion("Paso 4 de 4 - Confirmar y procesar")
    print(f"  {NEGRITA}Resumen de la operación:{RESET}")
    print()
    info(f"PDFs a procesar  : {len(pdfs)} archivo(s) en {carpeta}")
    if por_archivo:
        info(f"Salida           : Excel individual por PDF en {ruta_salida}")
    else:
        info(f"Salida           : Excel consolidado -> {ruta_salida}")
    info(f"Mover procesados : {'Sí -> ' + str(carpeta_procesados) if mover else 'No'}")
    print()

    confirmar = pedir_input("¿Continuar? (s/n)", default="s")
    if not confirmar or confirmar.lower() != "s":
        warn("Operación cancelada.")
        return

    # ── Procesamiento ──────────────────────────────────────
    seccion("Procesando…")

    # Importar los módulos del proyecto (están en src/ junto a este script)
    BASE = Path(__file__).resolve().parent
    sys.path.insert(0, str(BASE))

    import pdfplumber
    from extractor_encabezado import extraer_encabezado
    from extractor_detalle import extraer_detalle
    from generador_excel import generar_excel, obtener_documentos_existentes
    from procesar import filtrar_duplicados, mover_a_procesados

    # Logger silencioso (los mensajes se muestran en pantalla directamente)
    logger_silencioso = logging.getLogger("menu_cli")
    logger_silencioso.addHandler(logging.NullHandler())

    documentos = []
    errores = []
    warnings_archivos = {}

    for i, ruta_pdf in enumerate(pdfs, start=1):
        barra_progreso(i, len(pdfs))
        advertencias_pdf = []

        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                if not pdf.pages:
                    raise ValueError("El PDF no contiene páginas")
                page = pdf.pages[0]
                texto = page.extract_text()
                palabras = page.extract_words()

            if not texto:
                raise ValueError("No se pudo extraer texto (¿PDF escaneado?)")

            encabezado = extraer_encabezado(texto)

            faltantes = [c for c in ["ncf", "numero_documento", "fecha_documento"]
                         if not encabezado.get(c)]
            if faltantes:
                advertencias_pdf.append(f"Campos no encontrados: {', '.join(faltantes)}")

            detalle = extraer_detalle(palabras,
                                      numero_documento=encabezado.get("numero_documento"))
            if not detalle:
                advertencias_pdf.append("No se encontraron líneas de detalle")

            total = encabezado.get("total")
            if total and detalle:
                suma = sum((l.get("monto") or 0) for l in detalle)
                if abs(total - suma) >= 0.01:
                    advertencias_pdf.append(
                        f"No cuadra: encabezado={total:,.2f} vs detalle={suma:,.2f}"
                    )

            documentos.append({
                "encabezado": encabezado,
                "detalle": detalle,
                "ruta_pdf": ruta_pdf,
            })
            if advertencias_pdf:
                warnings_archivos[ruta_pdf.name] = advertencias_pdf

        except Exception as e:
            errores.append((ruta_pdf.name, str(e)))

        time.sleep(0.03)  # pequeña pausa para que la barra sea visible

    print()  # salto tras la barra de progreso

    # ── Generar Excel ──────────────────────────────────────
    if documentos:
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        if por_archivo:
            ruta_salida.mkdir(parents=True, exist_ok=True)
            for doc in documentos:
                numero = doc["encabezado"].get("numero_documento") or "sin_numero"
                ruta_excel = ruta_salida / f"{numero}.xlsx"
                docs_filtrados = filtrar_duplicados([doc], str(ruta_excel),
                                                    logger_silencioso)
                if docs_filtrados:
                    generar_excel(docs_filtrados, str(ruta_excel))
        else:
            docs_filtrados = filtrar_duplicados(documentos, str(ruta_salida),
                                                logger_silencioso)
            duplicados = len(documentos) - len(docs_filtrados)
            if duplicados > 0:
                warn(f"{duplicados} documento(s) duplicados omitidos (ya estaban en el Excel)")
            if docs_filtrados:
                generar_excel(docs_filtrados, str(ruta_salida))
                documentos = docs_filtrados  # solo mover los que sí se agregaron

        if mover and carpeta_procesados:
            mover_a_procesados(documentos, carpeta_procesados, logger_silencioso)

    # ── Resumen final ──────────────────────────────────────
    seccion("Resumen")
    exitosos = len(documentos)
    total_archivos = len(pdfs)

    ok(f"{exitosos} de {total_archivos} archivo(s) procesado(s) correctamente")

    if warnings_archivos:
        print()
        warn(f"{len(warnings_archivos)} archivo(s) con advertencias:")
        for nombre, avisos in warnings_archivos.items():
            print(f"    {AMARILLO}{nombre}{RESET}")
            for aviso in avisos:
                print(f"      {GRIS}· {aviso}{RESET}")

    if errores:
        print()
        error(f"{len(errores)} archivo(s) fallaron:")
        for nombre, motivo in errores:
            print(f"    {ROJO}{nombre}{RESET}")
            print(f"      {GRIS}· {motivo}{RESET}")

    if exitosos > 0:
        print()
        if por_archivo:
            ok(f"Excel(s) guardado(s) en: {ruta_salida}")
        else:
            ok(f"Excel guardado en: {ruta_salida}")
        if mover:
            ok(f"PDF procesados movidos a: {carpeta_procesados}")

    print()


# ── Menú principal ────────────────────────────────────────────────────────────

def main():
    while True:
        mostrar_cabecera()
        seccion("Menú principal")

        opcion = menu_opciones([
            "Procesar facturas PDF -> Excel",
            "Salir",
        ])

        if opcion == 0:
            flujo_procesar()
            print()
            input(f"  {GRIS}Presiona Enter para volver al menú principal…{RESET}")

        elif opcion == 1:
            limpiar()
            print()
            print(f"  {AZUL}Hasta luego.{RESET}")
            print()
            sys.exit(0)


if __name__ == "__main__":
    main()