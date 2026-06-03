@echo off
echo ================================
echo  CC Session Manager - Build
echo ================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Install dependencies
echo [1/3] Installing dependencies...
pip install PyQt5 pyinstaller --quiet
echo       Done.

:: Build exe
echo [2/3] Building exe...
pyinstaller --onefile --windowed --name "CCSessionManager" --hidden-import theme --hidden-import parser --hidden-import metadata --hidden-import i18n main.py
echo       Done.

:: Copy to project root for convenience
echo [3/3] Copying exe...
copy /Y dist\CCSessionManager.exe . >nul 2>&1

echo.
echo ================================
echo  Build complete!
echo  Output: dist\CCSessionManager.exe
echo ================================
pause
