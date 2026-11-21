<#
  GELİŞTİRME → CANLI yayın betiği.
  Kullanım:  powershell -ExecutionPolicy Bypass -File release.ps1 [-Publish] [-Install]
    (parametresiz)  testler + .exe + kurulum dosyası (build\out\TRCeviri-Kurulum.exe)
    -Publish        kurulumu GitHub 'pc-latest' sürümüne yükler (herkesin uygulamasında "Güncelle" çıkar)
    -Install        bu bilgisayardaki canlı uygulamayı kapatır, yeni sürümü kurar ve canlı çeviriyle açar
  Sürüm numarası trceviri\__init__.py içindeki __version__'dan okunur; yayından önce artırın.
#>
param([switch]$Publish, [switch]$Install)
$ErrorActionPreference = "Stop"
$B = $PSScriptRoot
$py = "$env:LOCALAPPDATA\TRCeviri\venv\Scripts\python.exe"
$W = "$env:LOCALAPPDATA\TRCeviri\build"
$ver = (Select-String -Path "$B\trceviri\__init__.py" -Pattern '"(\d+\.\d+\.\d+)"').Matches[0].Groups[1].Value
Write-Host "== TRÇeviri $ver" -ForegroundColor Green

Write-Host "1/4 testler"
& $py -m pytest -q "$B\tests"
if ($LASTEXITCODE -ne 0) { throw "Testler başarısız — yayın durduruldu" }

Write-Host "2/4 .exe derleniyor (PyInstaller)"
& $py -m PyInstaller --noconfirm --clean --windowed --name TRCeviri --icon "$B\installer\TRCeviri.ico" --paths "$B" `
  --collect-all rapidocr_onnxruntime --collect-binaries onnxruntime --collect-data onnxruntime --collect-all ctranslate2 `
  --collect-all winrt --collect-submodules winrt --hidden-import win32timezone --hidden-import win32com.client `
  --hidden-import sentencepiece --exclude-module onnxruntime.quantization --exclude-module onnxruntime.transformers `
  --add-data "$B\profiles;profiles" --add-data "$B\assets;assets" --add-data "$B\NASIL KULLANILIR.txt;." --add-data "$B\TRCeviri-TV.apk;." `
  --distpath "$W\dist" --workpath "$W\work" --specpath "$W" "$B\trceviri\__main__.py" | Out-Null
if (-not (Test-Path "$W\dist\TRCeviri\TRCeviri.exe")) { throw "PyInstaller başarısız" }

Write-Host "3/4 kurulum dosyası (Inno Setup)"
Push-Location "$B\installer"
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" /Q "/DDistDir=$W\dist\TRCeviri" "/DAppVer=$ver" "/O$W\out" TRCeviri.iss
Pop-Location
$setup = "$W\out\TRCeviri-Kurulum.exe"
if (-not (Test-Path $setup)) { throw "Kurulum dosyası oluşmadı" }
Write-Host "   $setup"

if ($Publish) {
  Write-Host "4/4 GitHub'a yayınlanıyor (pc-latest)"
  gh release delete pc-latest -R batuhankartalbc-SD/trtv -y --cleanup-tag 2>$null
  gh release create pc-latest $setup -R batuhankartalbc-SD/trtv -t "Brolis Game Translate $ver" `
    -n "Brolis Game Translate $ver — bilgisayar uygulaması kurulumu. Çift tıklayıp kurun (yönetici izni gerekmez)."
}

if ($Install) {
  Write-Host "Canlı ortam güncelleniyor"
  Get-Process TRCeviri -ErrorAction SilentlyContinue | Stop-Process -Force
  $proc = Start-Process $setup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS="desktopicon"' -PassThru
  $exe = "$env:LOCALAPPDATA\Programs\TRCeviri\TRCeviri.exe"
  $proc.WaitForExit(300000) | Out-Null                                   # kurulum bitsin
  $t0 = Get-Date                                                         # .tmp alt süreci de bitsin
  while (((Get-Date) - $t0).TotalSeconds -lt 60 -and (Get-Process "TRCeviri-Kurulum*" -ErrorAction SilentlyContinue)) { Start-Sleep 1 }
  Start-Sleep 4                                                          # kurulumun başlattığı kopya açılsın
  Get-Process TRCeviri -ErrorAction SilentlyContinue | Stop-Process -Force     # kurulumun açtığını kapat, canlı çeviriyle aç
  $t0 = Get-Date                                                         # tamamen kapansın (kısayollar serbest kalsın)
  while (((Get-Date) - $t0).TotalSeconds -lt 15 -and (Get-Process TRCeviri -ErrorAction SilentlyContinue)) { Start-Sleep 1 }
  Start-Process $exe -ArgumentList "--baslat" -WorkingDirectory (Split-Path $exe)
  Write-Host "Canlı: $ver çalışıyor" -ForegroundColor Green
}
