$ErrorActionPreference = 'Continue'
$runtime = Join-Path $PSScriptRoot 'work\runtime'
foreach ($name in @('web','api')) {
    $pidFile = Join-Path $runtime "$name.pid"
    if (Test-Path $pidFile) {
        $processId = [int](Get-Content $pidFile -Raw)
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) { Stop-Process -Id $processId -Force }
        Remove-Item -LiteralPath $pidFile -Force
    }
}
Write-Host 'Atlas services stopped.'
