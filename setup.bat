@echo off
setlocal

REM --- 1. Definiciones ---
REM Nombre de la carpeta del entorno virtual
set VENV_NAME=.venv
REM Nombre del archivo principal Python
set SCRIPT=costeando\main_interfaz_grafica.py

ECHO --- Iniciando proceso de empaquetado ---

REM --- 2. Crear Venv si no existe ---
if not exist %VENV_NAME%\Scripts\activate.bat (
    echo.
    REM LÍNEA CORREGIDA:
    echo Creando entorno virtual %VENV_NAME%...
    py -m venv %VENV_NAME%
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b
    )
)

REM --- 3. Activar el Entorno Virtual ---
echo Activando el entorno virtual...
call %VENV_NAME%\Scripts\activate.bat

REM --- 4. Instalar Dependencias DENTRO del Venv ---
echo Instalando/verificando dependencias en el venv...
REM (Asegurate de poner aqui TODAS las bibliotecas que usa tu script)
pip install pyinstaller pandas numpy platformdirs openpyxl

REM --- 5. Limpiar y Empaquetar ---
echo Limpiando carpetas anteriores (build/dist)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === Iniciando PyInstaller DENTRO del entorno virtual ===
pyinstaller --noconfirm --onefile --windowed %SCRIPT%
echo === PyInstaller finalizado ===

echo.
echo Empaquetado completado. El ejecutable esta en la carpeta dist\
pause
endlocal