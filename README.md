# EGEHID — Extracción de Notas de Crédito PDF a Excel

Herramienta de procesamiento por lotes que extrae los datos de Notas de
Crédito (PDF) de EGEHID y los consolida en un archivo Excel con la
estructura requerida por el portal de facturación electrónica.

## Campos extraídos

**Encabezado** (un valor por documento):
- Tipo de Documento (detectado automáticamente: Nota de Crédito, Nota de
  Débito o Factura)
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

**Detalle** (una línea por cada concepto de la factura):
- Descripción
- Monto

## Esquema del Excel generado

A diferencia de un Excel "tabular" tradicional, este proyecto usa un
**esquema de bloque por documento**, pensado para que el archivo se lea
de forma natural visualmente:

| Tipo Documento | NCF | NCF Modificado | Fecha Documento | No. Documento | ... | Monto | ID Documento | Observaciones |
|---|---|---|---|---|---|---|---|---|
| NOTA DE CREDITO | E340000000070 | E310000000181 | 02/06/2026 | 800001168 | ... | 166,881.78 | 800001168 | Reliquidación... |
| | RELIQ CONTRATO POTENCIA 2025 | | | | | 131,453.24 | 800001168 | |
| | RELIQ CONTRATO DC 2025 | | | | | 27,945.75 | 800001168 | |
| | RELIQ CONTRATO SIE 2025 | | | | | 5,612.09 | 800001168 | |
| | RELIQ CONTRATO CNE 2025 | | | | | 1,870.70 | 800001168 | |

- La **primera fila de cada documento** lleva el encabezado completo: el
  NCF real en la columna "NCF" y el total del documento en la columna
  "Monto".
- Las **filas siguientes** (una por cada línea de concepto) dejan vacías
  todas las columnas de encabezado, excepto: la columna "NCF" (que aquí
  lleva la **descripción** del concepto, no un NCF) y la columna "Monto"
  (que lleva el importe de ese concepto).
- La columna **"ID Documento (Nombre de archivo Origen)"** se repite en
  todas las filas de un mismo documento (encabezado y detalle), y es la
  que garantiza la relación encabezado-detalle de forma explícita, sin
  depender solo de la posición visual en la hoja.
- El siguiente documento empieza inmediatamente después, sin fila vacía
  de separación; su propia fila de encabezado ya marca el inicio del
  siguiente bloque.
- La fila de encabezado de cada documento se resalta con fondo azul claro
  y texto en negrita para distinguirla visualmente de las filas de
  detalle.
- Fechas y montos quedan con su tipo de dato real (`datetime` y `float`
  de Python, formato de fecha y de moneda en Excel), nunca como texto.

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> En Windows, si `pip install` falla por permisos, usa
> `pip install -r requirements.txt --user` o asegúrate de tener el
> entorno virtual activado (debe aparecer `(venv)` al inicio de la línea
> de comandos).

## Uso

Todos los comandos se ejecutan desde la carpeta `src/`.

### Un Excel consolidado con todas las facturas de una carpeta

```bash
python procesar.py --carpeta ../muestras --salida ../salida/resultado.xlsx
```

### Un Excel por cada factura

```bash
python procesar.py --carpeta ../muestras --salida ../salida --por-archivo
```

### Parámetros

| Parámetro | Obligatorio | Por defecto | Descripción |
|---|---|---|---|
| `--carpeta` | No | `muestras` | Carpeta que contiene los PDF a procesar |
| `--salida` | No | `salida/resultado.xlsx` | Ruta del Excel (o carpeta, si se usa `--por-archivo`) |
| `--por-archivo` | No | — | Genera un Excel independiente por cada PDF |
| `--log` | No | `logs/procesamiento.log` | Ruta del archivo de log |

## Pruebas automatizadas

El proyecto incluye un set de pruebas (`tests/test_extraccion.py`) que
valida la extracción contra resultados esperados conocidos del PDF de
muestra, además de casos de robustez ante campos faltantes:

```bash
python tests/test_extraccion.py
```

o, si tienes pytest instalado:

```bash
pip install pytest --break-system-packages
python -m pytest tests/ -v
```

Las pruebas cubren:
- Que el encabezado y el detalle del PDF de muestra se extraigan
  correctamente y con el tipo de dato esperado (fechas como `datetime`,
  montos como `float`).
- Que la suma de las líneas de detalle cuadre con el total del
  encabezado.
- Que el extractor **no lance excepciones** cuando faltan campos clave
  o no hay tabla de detalle reconocible — esto es lo que se prueba
  intencionalmente con el archivo `Nota_Credito_Prueba.pdf`: ese PDF no
  contiene los campos esperados a propósito, para verificar que el
  sistema registra el problema en el log y sigue procesando el resto
  del lote sin detenerse.

## Salida

El Excel generado tiene una sola hoja ("Facturacion") con el esquema de
bloque descrito arriba. El control de cuadre (verificar que la suma del
detalle coincida con el total del encabezado) ya no se muestra en una
hoja separada; en su lugar, **se registra como advertencia en el log**
si algún documento no cuadra (ver sección de Log).

## Log de procesamiento

Cada ejecución genera un log con tres niveles de mensaje:

- `INFO`: documento procesado correctamente, o resumen final
  (`X procesados, Y con error, de Z totales`).
- `WARNING`: el documento se procesó pero con alguna inconsistencia —
  campos clave no encontrados, sin líneas de detalle, o el total no
  cuadra con la suma del detalle. El documento **sigue incluido** en el
  Excel, con los campos faltantes vacíos.
- `ERROR`: el PDF no se pudo abrir o no tiene texto extraíble (por
  ejemplo, un PDF escaneado). Ese documento **no se incluye** en el
  Excel, pero el resto del lote continúa procesándose con normalidad.

## Estructura del proyecto

```
egehid_pdf2excel/
├── src/
│   ├── extractor_encabezado.py   # Extrae campos de encabezado (regex sobre anclas de texto)
│   ├── extractor_detalle.py      # Extrae líneas de detalle (por coordenadas)
│   ├── generador_excel.py        # Construye el Excel final con el esquema de bloque
│   └── procesar.py               # Script principal (CLI) / orquestador del lote
├── muestras/                     # PDF de ejemplo y casos de prueba de robustez
├── salida/                       # Excels generados (no se versiona en git)
├── logs/                         # Logs de procesamiento (no se versiona en git)
├── tests/
│   └── test_extraccion.py        # Pruebas automatizadas contra resultados esperados
├── .gitignore
├── requirements.txt
└── README.md
```

## Diseño y mantenibilidad

La extracción del encabezado se basa en **anclas de texto** (regex que
busca la etiqueta, p. ej. `"NCF :"`, y captura lo que sigue), no en
coordenadas absolutas. Esto permite que el sistema tolere pequeños
desplazamientos del PDF entre un documento y otro. Si en el futuro un
campo cambia de etiqueta o aparece un nuevo tipo de documento, basta con
editar el diccionario `PATRONES` en `extractor_encabezado.py`, sin tocar
el resto del código.

El procesamiento por lotes nunca se detiene por un PDF con error: cada
archivo se procesa de forma aislada y cualquier fallo o inconsistencia
queda registrado en el log con el motivo, permitiendo que el resto del
lote continúe.

## Limitaciones conocidas / próximos pasos

- Diseñado y probado contra **Notas de Crédito**. Si se procesan Facturas
  regulares u otro tipo de documento con campos distintos, hay que
  validar y, de ser necesario, ajustar `PATRONES` en
  `extractor_encabezado.py`.
- Asume PDF con texto nativo (no escaneado). Si llegaran PDF escaneados,
  se necesitaría agregar OCR (`pytesseract`), no incluido por ahora.
- Las líneas de detalle no incluyen cantidad ni precio unitario porque
  el formato real de EGEHID no los presenta por línea (solo "Concepto" y
  "Total RD$"); si en el futuro aparece un formato con esas columnas,
  habría que extenderlas en `extractor_detalle.py`.
