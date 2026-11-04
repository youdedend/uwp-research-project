# Windows wrapper for bootstrap.py. Run from the repository root, e.g.:
#   powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\bootstrap.ps1 -WithBaseline -Audit
[CmdletBinding()]
param(
    [string]$WorkDir,
    [switch]$WithBaseline,
    [switch]$Audit
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) { throw 'Python 3 was not found on PATH (python or py).' }

$arguments = @()
if ($python.Name -eq 'py.exe') { $arguments += @('-3') }
$arguments += @((Join-Path $scriptDir 'bootstrap.py'))
if ($WorkDir) { $arguments += @('--work-dir', $WorkDir) }
if ($WithBaseline) { $arguments += @('--with-baseline') }
if ($Audit) { $arguments += @('--audit') }

& $python.Source @arguments
exit $LASTEXITCODE
