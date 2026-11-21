@echo off
rem GELİŞTİRME ortamı: kaynak koddan çalışır, ayarları %APPDATA%\TRCeviri-Dev'de tutar, canlı uygulamaya ve TV'ye dokunmaz.
chcp 65001 >nul
cd /d "%~dp0"
set "TRCEVIRI_DEV=1"
set "VENV=%LOCALAPPDATA%\TRCeviri\venv"
if not exist "%VENV%\Scripts\pythonw.exe" (echo Once run.bat ile kurulum yapin & pause & exit /b 1)
start "" "%VENV%\Scripts\pythonw.exe" -m trceviri %*