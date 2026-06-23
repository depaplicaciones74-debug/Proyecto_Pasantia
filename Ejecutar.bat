@echo off
chcp 65001 >nul
setlocal

set "RAIZ=%~dp0"
if "%RAIZ:~-1%"=="" set "RAIZ=%RAIZ:~0,-1%"

if exist "%RAIZ%\venv\Scripts\python.exe" (
"%RAIZ%\venv\Scripts\python.exe" "%RAIZ%\src\procesar.py"
) else (
echo [ERROR] No se encontro el entorno virtual.
echo Ejecute primero instalar.bat
pause
exit /b 1
)

pause
