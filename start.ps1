$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtime = Join-Path $root 'work\runtime'
$apiDir = Join-Path $root 'apps\api'
$webDir = Join-Path $root 'apps\web'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { $candidate = Join-Path $env:ProgramFiles 'nodejs\node.exe'; if (Test-Path $candidate) { $node = Get-Item $candidate } }
if (-not $node) { throw 'Node.js 22+ is required. Install it from https://nodejs.org/ and run this script again.' }
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$python = if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') { $pythonCommand.Source } else { $null }
$venvPython = Join-Path $apiDir '.venv\Scripts\python.exe'
$venvConfig = Join-Path $apiDir '.venv\pyvenv.cfg'
if (-not $python -and (Test-Path $venvConfig)) {
    $basePython = Select-String -Path $venvConfig -Pattern '^executable\s*=\s*(.+)$' | Select-Object -First 1
    if ($basePython) { $python = $basePython.Matches[0].Groups[1].Value.Trim() }
}
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $python -and $pyLauncher) {
    & $pyLauncher.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null | ForEach-Object { $python = $_ }
}
if (-not $python -or -not (Test-Path $python)) { throw 'Python 3.12 is required. Install it from https://www.python.org/downloads/windows/ and run this script again.' }

if (-not (Test-Path $venvPython)) { & $python -m venv (Join-Path $apiDir '.venv') }
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $apiDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Installing API dependencies failed.' }

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
$npm = if ($npmCommand) { $npmCommand.Source } else { Join-Path $env:ProgramFiles 'nodejs\npm.cmd' }
if (-not (Test-Path $npm)) { throw 'npm was not found. Reinstall Node.js with npm included.' }
if (-not (Test-Path (Join-Path $webDir 'node_modules\next'))) {
    Push-Location $webDir
    try { & $npm install; if ($LASTEXITCODE -ne 0) { throw 'Installing web dependencies failed.' } } finally { Pop-Location }
}

foreach ($port in @(8000, 3000)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { throw "Port $port is already in use (PID $($listener.OwningProcess)). Stop that process before starting Atlas." }
}

$env:APP_ENV = 'development'
$env:NEXT_DIST_DIR = '.next-runtime'
$env:DATABASE_URL = 'sqlite:///./atlas.db'
$env:CORS_ORIGINS = 'http://127.0.0.1:3000'
$api = Start-Process -FilePath $venvPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $apiDir -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'api.log') -RedirectStandardError (Join-Path $runtime 'api-error.log')
$api.Id | Set-Content (Join-Path $runtime 'api.pid')
$nextCli = Join-Path $webDir 'node_modules\next\dist\bin\next'
$web = Start-Process -FilePath $node.Source -ArgumentList @($nextCli,'dev','-H','127.0.0.1') -WorkingDirectory $webDir -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'web.log') -RedirectStandardError (Join-Path $runtime 'web-error.log')
$web.Id | Set-Content (Join-Path $runtime 'web.pid')

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 2
        $page = Invoke-WebRequest 'http://127.0.0.1:3000' -TimeoutSec 3 -UseBasicParsing
        if ($health.status -eq 'ok' -and $page.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    if ($api.HasExited -or $web.HasExited) { break }
}
if (-not $ready) {
    Get-Content (Join-Path $runtime 'api-error.log') -ErrorAction SilentlyContinue | Write-Host
    Get-Content (Join-Path $runtime 'web-error.log') -ErrorAction SilentlyContinue | Write-Host
    throw 'Atlas did not become ready. Check work/runtime logs.'
}
Write-Host 'Atlas is ready: http://127.0.0.1:3000' -ForegroundColor Green
Start-Process 'http://127.0.0.1:3000'
