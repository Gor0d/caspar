$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoPath
function Assert-Command { if ($LASTEXITCODE -ne 0) { throw 'O comando anterior falhou; a instalação foi interrompida.' } }
python -m venv .venv
Assert-Command
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock
Assert-Command
Push-Location frontend
try {
    npm.cmd ci --no-audit --no-fund
    Assert-Command
    npm.cmd run build
    Assert-Command
} finally { Pop-Location }
& .\.venv\Scripts\python.exe -m backend.cli init
Assert-Command
& $PSScriptRoot\Protect-Data.ps1
Write-Host 'CASPAR instalado. Execute: .\scripts\Start.ps1'
