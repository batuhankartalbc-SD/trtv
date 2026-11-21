@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\TRCeviri\venv"
if not exist "%VENV%\Scripts\python.exe" (echo Once run.bat ile kurulum yapin & pause & exit /b 1)
"%VENV%\Scripts\python.exe" -m pip install -q pyinstaller
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name TRCeviri ^
  --collect-all rapidocr_onnxruntime --add-data "profiles;profiles" ^
  --distpath "%LOCALAPPDATA%\TRCeviri\dist" --workpath "%LOCALAPPDATA%\TRCeviri\build" ^
  trceviri\__main__.py
echo.
echo Hazir: %LOCALAPPDATA%\TRCeviri\dist\TRCeviri\TRCeviri.exe
pause
