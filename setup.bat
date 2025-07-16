@echo off
REM Script para empaquetar el script principal con PyInstaller

REM Nombre del archivo principal Python
set SCRIPT=costeando\main_interfaz_grafica.py

REM Verificar si PyInstaller está instalado
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller no esta instalado. Instalando...
    pip install pyinstaller
)

REM Eliminar carpetas build y dist anteriores (opcional)
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Empaquetar con PyInstaller
pyinstaller --noconfirm --onefile --windowed %SCRIPT%

echo.
echo Empaquetado completado. El ejecutable esta en la carpeta dist\
pause
