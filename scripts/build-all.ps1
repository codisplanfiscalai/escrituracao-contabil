param([string]$PythonX86 = '', [string]$PythonX64 = '', [switch]$NoCache)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
foreach ($arch in @('x86', 'x64')) {
    $exe = if ($arch -eq 'x86') { $PythonX86 } else { $PythonX64 }
    if ($exe) { & $exe scripts/build.py windows --arch $arch --install-build-tools }
    elseif ($arch -eq 'x86') { py -3.13-32 scripts/build.py windows --arch x86 --install-build-tools }
    else { py -3.13-64 scripts/build.py windows --arch x64 --install-build-tools }
    if ($LASTEXITCODE -ne 0) { throw "Falha no build Windows $arch" }
}
$extra = @(); if ($NoCache) { $extra += '--no-cache' }
if ($PythonX64) { & $PythonX64 scripts/build.py container @extra }
else { py -3.13-64 scripts/build.py container @extra }
if ($LASTEXITCODE -ne 0) { throw 'Falha no build Docker' }
