# Bloodborne Xbox UWP - Phase 1/2a + item-2 step-1 release push
# Run in PowerShell on any machine with git + gh signed in to youdedend/Test-project.
# Pushes the prepared commit d31be49 (2a recovery ladder + o1heap staging arena) onto
# arena/8ac58bdb-test-project; the Xbox build workflow then publishes the [release]
# pre-release automatically (xbox-alpha-1.0.<YYDDD>.<HHMM>).
# Fallback: staging_arena=0 in bbport.ini (or BB_STAGING_ARENA=0) restores the legacy
# staging path exactly; the 2a recovery ladder is independent of it.
$ErrorActionPreference = 'Stop'
$tmp = Join-Path $env:TEMP 'bb-release-2a-step1'
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
git clone https://github.com/youdedend/Test-project.git $tmp
Set-Location $tmp
git fetch origin arena/8ac58bdb-test-project
git checkout -B arena/8ac58bdb-test-project origin/arena/8ac58bdb-test-project
git fetch "$PSScriptRoot\phase1-2a-step1.bundle" 'refs/heads/arena/8ac58bdb-test-project:refs/bb/step1'
git merge --ff-only refs/bb/step1
git push origin arena/8ac58bdb-test-project
Write-Host 'Pushed. Watching CI...'
gh run watch (gh run list -R youdedend/Test-project --branch arena/8ac58bdb-test-project --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
gh release list -R youdedend/Test-project --limit 2
