$ErrorActionPreference = 'Stop'
$repoPath = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Push-Location -LiteralPath $repoPath
try {
    $dataPath = (& .\.venv\Scripts\python.exe -c "from backend.config import Settings; print(Settings().prepare().caspar_data_dir)").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível validar o diretório de dados.' }
    $resolvedDataPath = [System.IO.Path]::GetFullPath($dataPath)
    if ($resolvedDataPath.StartsWith($repoPath, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Os dados devem ficar fora do repositório.' }
    $currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    # Explicitly protect this dedicated CASPAR directory, preserving access for the owner and SYSTEM.
    & icacls.exe $resolvedDataPath /inheritance:r /grant:r "*${currentSid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao proteger o diretório com ACL.' }
} finally { Pop-Location }
