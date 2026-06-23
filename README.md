# EGEHID — Extracción de Notas de Crédito PDF a Excel

Herramienta de procesamiento por lotes que extrae los datos de Notas de Crédito (PDF) de EGEHID y los consolida en un archivo Excel con la estructura requerida por el portal de facturación electrónica.

---

## Estructura del proyecto

```
Proyecto_Pasantia/
├── src/
│   ├── procesar.py               # Script principal / orquestador del lote
│   ├── extractor_encabezado.py   # Extrae campos de encabezado (regex sobre anclas de texto)
│   ├── extractor_detalle.py      # Extrae líneas de detalle (por coordenadas)
│   └── generador_excel.py        # Construye el Excel final con el esquema de bloque
├── tests/
│   └── test_extraccion.py        # Pruebas automatizadas
├── muestras/                     # Coloca aquí los PDF a procesar
├── salida/                       # El Excel generado aparece aquí
├── logs/                         # Logs de cada ejecución
├── procesados/                   # Los PDF ya procesados se mueven aquí automáticamente
├── requirements.txt
└── README.md
```

> Las carpetas `muestras/`, `salida/`, `logs/` y `procesados/` se crean
> automáticamente la primera vez que se ejecuta `procesar.py`. No hace falta crearlas a mano.

---

## Instalación

```bash
git clone https://github.com/depaplicaciones74-debug/Proyecto_Pasantia
cd Proyecto_Pasantia
python -m venv venv
```

Activar el entorno virtual:

```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Uso

Todos los comandos se ejecutan desde la carpeta `src/`.

```bash
cd src
```

### Excel consolidado con todos los PDF de la carpeta muestras/

```bash
python procesar.py
```

### Especificar carpeta y archivo de salida manualmente

```bash
python procesar.py --carpeta ../muestras --salida ../salida/resultado.xlsx
```

### Un Excel independiente por cada PDF

```bash
python procesar.py --por-archivo
```

### No mover los PDF a procesados/ tras ejecutar

```bash
python procesar.py --no-mover
```

### Parámetros disponibles

| Parámetro | Por defecto | Descripción |
|---|---|---|
| `--carpeta` | `muestras/` | Carpeta con los PDF a procesar |
| `--salida` | `salida/resultado.xlsx` | Ruta del Excel de salida |
| `--por-archivo` | — | Genera un Excel por cada PDF |
| `--log` | `logs/procesamiento.log` | Ruta del archivo de log |
| `--carpeta-procesados` | `procesados/` | Carpeta destino de los PDF ya procesados |
| `--no-mover` | — | No mover los PDF tras procesarlos |

---

## Campos extraídos

**Encabezado** (un valor por documento):
- Tipo de Documento (detectado automáticamente: Nota de Crédito, Nota de Débito o Factura)
- NCF
- NCF Modificado
- Fecha de Documento
- No. de Documento
- Indicador de Bien/Servicio (constante = 1, requerido por el portal)
- Fecha de Vencimiento
- RNC del Cliente
- Cliente
- Monto (total del documento)
- Observaciones

**Detalle** (una fila por cada concepto de la factura):
- Descripción
- Monto

---

## Esquema del Excel generado

El archivo usa un esquema de bloque por documento:

| Tipo Documento | NCF | NCF Modificado | Fecha Documento | No. Documento | ... | Monto | ID Documento | Observaciones |
|---|---|---|---|---|---|---|---|---|
| NOTA DE CREDITO | E340000000070 | E310000000181 | 02/06/2026 | 800001168 | ... | 166,881.78 | 800001168 | Reliquidación... |
| | RELIQ CONTRATO POTENCIA 2025 | | | | | 131,453.24 | 800001168 | |
| | RELIQ CONTRATO DC 2025 | | | | | 27,945.75 | 800001168 | |
| | RELIQ CONTRATO SIE 2025 | | | | | 5,612.09 | 800001168 | |
| | RELIQ CONTRATO CNE 2025 | | | | | 1,870.70 | 800001168 | |

- La **primera fila** de cada documento lleva el encabezado completo con el NCF real y el total en "Monto".
- Las **filas de detalle** dejan vacías todas las columnas de encabezado, excepto "NCF" (que lleva la descripción del concepto) y "Monto" (que lleva el importe de ese concepto).
- La columna **"ID Documento"** se repite en todas las filas del mismo documento para mantener la relación encabezado-detalle sin depender de la posición visual.
- El siguiente documento empieza inmediatamente después, sin fila vacía de separación.
- La fila de encabezado de cada documento se resalta en **azul claro con negrita**.
- Fechas y montos se guardan con su tipo de dato real (`datetime` y `float`), nunca como texto.

---

## Log de procesamiento

Cada ejecución genera un log en `logs/procesamiento.log` con tres niveles:

- `INFO` — documento procesado correctamente, o resumen final.
- `WARNING` — el documento se procesó pero con alguna inconsistencia: campo faltante, sin líneas de detalle, o el total no cuadra con la suma del detalle. El documento **sí se incluye** en el Excel.
- `ERROR` — el PDF no se pudo abrir o no tiene texto extraíble (PDF escaneado). El documento **no se incluye** en el Excel, pero el resto del lote continúa con normalidad.

---

## Pruebas automatizadas

```bash
# Desde la raíz del proyecto
python tests/test_extraccion.py

# O con pytest
pip install pytest
python -m pytest tests/ -v
```

Las pruebas cubren:
- Que el encabezado y el detalle se extraigan correctamente con el tipo de dato esperado (fechas como `datetime`, montos como `float`).
- Que la suma de las líneas de detalle cuadre con el total del encabezado.
- Que el extractor no lance excepciones cuando faltan campos clave o no hay tabla de detalle reconocible, verificando que el sistema registra el problema en el log y continúa procesando el resto del lote.

---

## Diseño y mantenibilidad

La extracción del encabezado se basa en **anclas de texto** (regex que busca la etiqueta, por ejemplo `"NCF :"`, y captura lo que sigue), no en coordenadas absolutas. Esto permite tolerar pequeños desplazamientos del PDF entre un documento y otro. Si en el futuro un campo cambia de etiqueta o aparece un nuevo tipo de documento, basta con editar el diccionario `PATRONES` en `extractor_encabezado.py`.

El procesamiento por lotes nunca se detiene por un PDF con error: cada archivo se procesa de forma aislada y cualquier fallo queda registrado en el log con el motivo.

---

## Limitaciones conocidas

- Diseñado y probado contra **Notas de Crédito EGEHID**. Otros tipos de documento pueden requerir ajustes en `PATRONES` dentro de `extractor_encabezado.py`.
- Solo funciona con **PDF de texto nativo** (no escaneados). Para PDFs escaneados se necesitaría agregar OCR (`pytesseract`).
- Las líneas de detalle no incluyen cantidad ni precio unitario, ya que el formato EGEHID solo presenta "Concepto" y "Total RD$" por línea.

---

## Instalación y uso rápido (Windows)

Para usuarios de Windows que prefieran no usar la terminal, el repositorio incluye dos scripts de acceso rápido.

### instalar.bat

Descarga automáticamente los archivos del proyecto desde GitHub, crea las carpetas necesarias, el entorno virtual e instala las dependencias. Solo hace falta ejecutarlo una vez.

1. Descarga `instalar.bat` y `ejecutar.bat` en la carpeta donde quieras instalar el proyecto
2. Descarga también `requirements.txt` y colócalo en la misma carpeta
3. Haz doble clic en **`instalar.bat`**

El instalador hace todo automáticamente:
- Crea las carpetas `muestras/`, `salida/`, `logs/`, `procesados/` y `src/`
- Descarga los scripts Python desde GitHub a `src/`
- Crea el entorno virtual (`venv/`)
- Instala las dependencias

> Si Python no está instalado, descárgalo desde https://www.python.org y vuelve a ejecutar `instalar.bat`.

### ejecutar.bat

Una vez instalado, para procesar PDFs:

1. Copia los PDF a la carpeta **`muestras\`**
2. Haz doble clic en **`ejecutar.bat`**
3. El Excel consolidado aparece en **`salida\resultado.xlsx`**
4. Los PDF procesados se mueven automáticamente a **`procesados\`**
