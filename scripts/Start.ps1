$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Execute scripts\Setup.ps1 primeiro.' }
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Compile o frontend: cd frontend; npm.cmd run build' }
Write-Host 'CASPAR: http://127.0.0.1:8000 — Ctrl+C para encerrar'
& .\.venv\Scripts\python.exe -m backend.cli serve
