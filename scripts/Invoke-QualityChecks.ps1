[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$settingsPath = Join-Path $repositoryRoot 'PSScriptAnalyzerSettings.psd1'
$paths = @(
    (Join-Path $repositoryRoot 'powershell'),
    (Join-Path $repositoryRoot 'scripts')
)

if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
    throw 'PSScriptAnalyzer is required. Install-Module PSScriptAnalyzer -Scope CurrentUser'
}

$results = @($paths | Invoke-ScriptAnalyzer -Settings $settingsPath)
if ($results.Count -gt 0) {
    $results | Format-Table ScriptName, Line, RuleName, Severity, Message -Wrap -AutoSize
    throw "PSScriptAnalyzer reported $($results.Count) finding(s)."
}

Write-Output 'PowerShell analysis passed.'
