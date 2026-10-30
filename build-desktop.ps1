$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv-desktop
& ./.venv-desktop/Scripts/python.exe -m pip install -r requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости сборки' }
$grandWeb = Join-Path $PSScriptRoot 'web'
$grandIcon = Join-Path $PSScriptRoot 'assets/copilot.ico'
& ./.venv-desktop/Scripts/python.exe -m PyInstaller --noconfirm --onefile --windowed --name 'Grand Copilot' --distpath dist-native --workpath build --specpath build --add-data "$grandWeb;web" --icon $grandIcon desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Не удалось собрать приложение' }
Write-Host 'Готово: dist-native/Grand Copilot.exe'
