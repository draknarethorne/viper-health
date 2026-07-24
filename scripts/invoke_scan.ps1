<#
.SYNOPSIS
    Convenience wrapper for the viper-health unified scan.

.DESCRIPTION
    Delegates to the packaged Python CLI (viper_health.cli.scan). Prefers the
    repo virtual environment interpreter if present, otherwise falls back to
    'python' on PATH. All arguments are forwarded to the CLI.

.EXAMPLE
    ./scripts/invoke_scan.ps1 --root C:\Users\me\AppData --console-summary
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}

& $python -m viper_health.cli.scan @Args
exit $LASTEXITCODE
