# Bloodborne Xbox UWP - Phase 1/2a release push (item 2 stage 2a: pre-allocation recovery ladder)
# Run in PowerShell on any machine with git + gh signed in to youdedend/Test-project.
# Pushes the prepared commit 681384b onto arena/8ac58bdb-test-project; the Xbox build
# workflow then publishes the [release] pre-release automatically.
$ErrorActionPreference = 'Stop'
$tmp = Join-Path $env:TEMP 'bb-release-2a'
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
git clone https://github.com/youdedend/Test-project.git $tmp
Set-Location $tmp
git fetch origin arena/8ac58bdb-test-project
git checkout -B arena/8ac58bdb-test-project origin/arena/8ac58bdb-test-project
git fetch "$PSScriptRoot\phase1-2a.bundle" 'refs/heads/arena/8ac58bdb-test-project:refs/bb/2a'
git merge --ff-only refs/bb/2a
git push origin arena/8ac58bdb-test-project
Write-Host 'Pushed. Watching CI...'
gh run watch (gh run list -R youdedend/Test-project --branch arena/8ac58bdb-test-project --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
gh release list -R youdedend/Test-project --limit 2
