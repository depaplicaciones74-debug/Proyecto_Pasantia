@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo  EGEHID — Instalador del proyecto
echo ============================================================
echo.

REM Carpeta raíz del proyecto = carpeta donde está este .bat
set "RAIZ=%~dp0"
REM Quitar barra final si existe
if "%RAIZ:~-1%"=="\" set "RAIZ=%RAIZ:~0,-1%"

echo [1/4] Creando carpetas del proyecto...
for %%D in (muestras salida logs procesados src tests) do (
    if not exist "%RAIZ%\%%D" (
        mkdir "%RAIZ%\%%D"
        echo        + %%D
    ) else (
        echo        = %%D  (ya existe)
    )
)
echo.

echo [2/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Descargalo desde https://www.python.org
    pause
    exit /b 1
)
python --version
echo.

echo [3/4] Creando entorno virtual (venv)...
if not exist "%RAIZ%\venv" (
    python -m venv "%RAIZ%\venv"
    echo        Entorno virtual creado.
) else (
    echo        El entorno virtual ya existe.
)
echo.

echo [4/4] Instalando dependencias...
call "%RAIZ%\venv\Scripts\activate.bat"
pip install --upgrade pip --quiet
pip install -r "%RAIZ%\requirements.txt"
echo.

echo ============================================================
echo  Instalacion completada correctamente.
echo.
echo  Para procesar PDFs, pon los archivos en:
echo    %RAIZ%\muestras\
echo.
echo  Luego ejecuta:
echo    ejecutar.bat
echo.
echo  O desde la linea de comandos:
echo    cd "%RAIZ%\src"
echo    ..\venv\Scripts\python procesar.py
echo ============================================================
echo.
pause