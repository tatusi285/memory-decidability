<#
.SYNOPSIS
    Windows task runner for the memory-decidability artifact.

.EXAMPLE
    .\tasks.ps1 test
    .\tasks.ps1 build
    .\tasks.ps1 help
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'test', 'verify', 'audit', 'tables', 'figures', 'build', 'lint', 'clean')]
    [string]$Task = 'help',

    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Step {
    param([string[]]$Arguments)
    Write-Host "> $Python $($Arguments -join ' ')" -ForegroundColor Cyan
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "step failed with exit code $LASTEXITCODE"
    }
}

switch ($Task) {
    'help' {
        Write-Host 'tasks.ps1 <task> [-Python <exe>]' -ForegroundColor Yellow
        Write-Host '  test     run the unit test suite'
        Write-Host '  verify   recompute the 62 published values from data/'
        Write-Host '  audit    run the design audit'
        Write-Host '  tables   regenerate every table as Markdown'
        Write-Host '  figures  regenerate every figure as SVG'
        Write-Host '  build    verify + audit + tables + figures'
        Write-Host '  lint     ruff check'
        Write-Host '  clean    remove analysis_out/'
    }
    'test' { Invoke-Step @('-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-v') }
    'verify' { Invoke-Step @('-m', 'memdec', 'verify') }
    'audit' { Invoke-Step @('-m', 'memdec', 'audit') }
    'tables' { Invoke-Step @('-m', 'memdec', 'tables') }
    'figures' { Invoke-Step @('-m', 'memdec', 'figures') }
    'build' { Invoke-Step @('-m', 'memdec', 'build') }
    'lint' { Invoke-Step @('-m', 'ruff', 'check', 'memdec', 'tests') }
    'clean' {
        if (Test-Path -LiteralPath 'analysis_out') {
            Remove-Item -LiteralPath 'analysis_out' -Recurse -Force
        }
        Write-Host 'removed analysis_out/' -ForegroundColor Green
    }
}
