@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\TRCeviri\venv"
set "MARK=%VENV%\.kurulum-v3"

if exist "%MARK%" goto run

if exist "%VENV%\Scripts\python.exe" goto deps
echo [TRCeviri] Ilk kurulum yapiliyor, birkac dakika surebilir...
set "PY="
where py >nul 2>nul && set "PY=py -3.12"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not defined PY (
  echo Python 3.12 bulunamadi. Kuruluyor...
  winget install --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
)
%PY% -m venv "%VENV%" || (echo Sanal ortam olusturulamadi & pause & exit /b 1)

:deps
echo [TRCeviri] Paketler kuruluyor...
"%VENV%\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || (echo Paketler kurulamadi & pause & exit /b 1)
rem Ekran karti hizlandirmasi (DirectML): CPU surumunu GPU surumuyle degistir
"%VENV%\Scripts\python.exe" -m pip uninstall -y -q onnxruntime >nul 2>nul
"%VENV%\Scripts\python.exe" -m pip install -q --disable-pip-version-check onnxruntime-directml || "%VENV%\Scripts\python.exe" -m pip install -q onnxruntime
echo ok> "%MARK%"

:run
start "" "%VENV%\Scripts\pythonw.exe" -m trceviri %*
endlocal