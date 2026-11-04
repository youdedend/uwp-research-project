#requires -Version 5.1
<#
.SYNOPSIS
Run the pristine upstream NSMBW Windows PC baseline for the Xbox port.

.DESCRIPTION
This wrapper performs the order documented by upstream in
projects/nsmbw/BUILDING.md:

  1. pinned source bootstrap + read-only UWP audit;
  2. Launcher/Prepare-Dependencies.ps1 and Prepare-PortableTools.ps1;
  3. projects/nsmbw/tools/unpack_game.py (validates SMNE01 revision 1);
  4. projects/nsmbw/tools/prelink_rels.py;
  5. projects/nsmbw/tools/rebuild-all.ps1, which builds the translator, runs
     translate-recursive, emit-base-manifest, generate-data-init and
     emit-build-shards, configures native-build if needed, then builds the
     WiiCompiled target;
  6. verifies WiiCompiled.exe plus the shard manifest and captures
     native-build/compile_commands.json for the later Store compile replay.

The extracted game folder stays where you put it. Upstream's unpack step
creates translator inputs under ports/nsmbw-xbox/work/game, and the
generated game code stays inside the ignored work clone. Do not copy either
into tracked files or redistribute them.

This script does not apply any Xbox patches. Phase 1 is deliberately the
pristine upstream control build. The manual title -> World 1-1 -> save/reload
smoke test is still required after the build.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\run-phase1-pc.ps1 `
  -GameDir "D:\Games\NSMBW-SMNE01-rev1" -WithBaseline -CreateGameLink

.EXAMPLE
powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\run-phase1-pc.ps1 `
  -GameDir "D:\Games\NSMBW-SMNE01-rev1" -CheckOnly
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameDir,

    [string]$WorkDir,

    [ValidateRange(1, 64)]
    [int]$Threads = 10,

    [ValidateRange(1, 64)]
    [int]$Jobs = 10,

    [switch]$WithBaseline,
    [switch]$SkipBootstrap,
    [switch]$SkipPrepare,
    [switch]$CheckOnly,
    [switch]$CreateGameLink,
    [switch]$Launch,
    [switch]$AllowDirty
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$script:Checks = New-Object System.Collections.ArrayList
$script:StartedAt = Get-Date
$script:Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Get-FullPath([string]$Path) {
    return [IO.Path]::GetFullPath($Path)
}

function Add-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][ValidateSet('pass', 'warn', 'fail', 'pending')][string]$Status,
        [string]$Detail = ''
    )
    [void]$script:Checks.Add([pscustomobject]@{
        name = $Name
        status = $Status
        detail = $Detail
    })
    $prefix = switch ($Status) {
        'pass' { '[pass]' }
        'warn' { '[warn]' }
        'fail' { '[fail]' }
        default { '[ .. ]' }
    }
    if ($Detail) {
        Write-Host "$prefix $Name - $Detail"
    } else {
        Write-Host "$prefix $Name"
    }
}

function Test-IsUnderPath {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$Parent
    )
    $candidateFull = (Get-FullPath $Candidate).TrimEnd('\')
    $parentFull = (Get-FullPath $Parent).TrimEnd('\')
    return $candidateFull.Equals($parentFull, [StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($parentFull + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Invoke-Capture {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory
    )

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($WorkingDirectory) {
            Push-Location -LiteralPath $WorkingDirectory
            try {
                $output = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
                $code = $LASTEXITCODE
            } finally {
                Pop-Location
            }
        } else {
            $output = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
            $code = $LASTEXITCODE
        }
    } finally {
        $ErrorActionPreference = $oldPreference
    }

    return [pscustomobject]@{
        ExitCode = [int]$code
        Output = @($output)
        Text = (@($output) -join "`n").Trim()
    }
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory
    )

    Write-Host ""
    Write-Host "=== $Name ==="
    Write-Host "    $FilePath $($Arguments -join ' ')"
    if ($WorkingDirectory) { Write-Host "    cwd: $WorkingDirectory" }

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($WorkingDirectory) {
            Push-Location -LiteralPath $WorkingDirectory
            try {
                & $FilePath @Arguments
                $code = $LASTEXITCODE
            } finally {
                Pop-Location
            }
        } else {
            & $FilePath @Arguments
            $code = $LASTEXITCODE
        }
    } finally {
        $ErrorActionPreference = $oldPreference
    }

    if ($code -ne 0) {
        throw "$Name failed with exit code $code."
    }
}

$script:PowerShellExe = (Get-Process -Id $PID).Path
if (-not $script:PowerShellExe) { $script:PowerShellExe = 'powershell.exe' }

function Invoke-PowerShellFile {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory
    )

    $allArguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $Arguments
    Invoke-NativeChecked -Name $Name -FilePath $script:PowerShellExe -Arguments $allArguments `
        -WorkingDirectory $WorkingDirectory
}

$script:PythonExe = $null
$script:PythonPrefix = @()

function Resolve-Python {
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) {
        $script:PythonExe = $candidate.Source
        $script:PythonPrefix = @()
        return $true
    }
    $candidate = Get-Command py -ErrorAction SilentlyContinue
    if ($candidate) {
        $script:PythonExe = $candidate.Source
        $script:PythonPrefix = @('-3')
        return $true
    }
    return $false
}

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory
    )
    Invoke-NativeChecked -Name $Name -FilePath $script:PythonExe `
        -Arguments ($script:PythonPrefix + $Arguments) -WorkingDirectory $WorkingDirectory
}

function Get-GameRoot {
    param([Parameter(Mandatory = $true)][string]$Path)

    foreach ($candidate in @($Path, (Join-Path $Path 'DATA'))) {
        if ((Test-Path -LiteralPath (Join-Path $candidate 'files') -PathType Container) -and
            (Test-Path -LiteralPath (Join-Path $candidate 'sys\boot.bin') -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $candidate 'sys\main.dol') -PathType Leaf)) {
            return Get-FullPath $candidate
        }
    }
    return $null
}

function Get-ExpectedCommit {
    param([Parameter(Mandatory = $true)][string]$LockPath)

    $lock = Get-Content -LiteralPath $LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $repo = @($lock.repositories | Where-Object { $_.id -eq 'nsmbw' })[0]
    if (-not $repo -or -not $repo.commit) {
        throw "sources.lock.json does not contain an nsmbw commit: $LockPath"
    }
    return [string]$repo.commit
}

function Test-PinnedClone {
    param(
        [Parameter(Mandatory = $true)][string]$ClonePath,
        [Parameter(Mandatory = $true)][string]$ExpectedCommit
    )

    if (-not (Test-Path -LiteralPath (Join-Path $ClonePath '.git'))) {
        Add-Check 'NSMBW pinned clone' 'fail' "missing: $ClonePath"
        return $false
    }

    $headResult = Invoke-Capture -FilePath 'git' -Arguments @('-C', $ClonePath, 'rev-parse', 'HEAD')
    $head = $headResult.Text.Trim()
    if ($headResult.ExitCode -ne 0 -or $head -ne $ExpectedCommit) {
        Add-Check 'NSMBW pinned clone' 'fail' "HEAD is '$head'; lock wants '$ExpectedCommit'"
        return $false
    }

    $statusResult = Invoke-Capture -FilePath 'git' `
        -Arguments @('-C', $ClonePath, 'status', '--porcelain', '--untracked-files=normal')
    $dirtyLines = @($statusResult.Output | Where-Object { $_ -and $_.Trim() })
    $script:CloneDirtyLines = $dirtyLines

    if ($dirtyLines.Count -eq 0) {
        Add-Check 'NSMBW pinned clone' 'pass' "clean at $($ExpectedCommit.Substring(0, 12))"
        return $true
    }

    $summary = ($dirtyLines | Select-Object -First 12) -join '; '
    if ($AllowDirty) {
        Add-Check 'NSMBW pinned clone' 'warn' "dirty, but -AllowDirty was supplied: $summary"
        return $true
    }

    Add-Check 'NSMBW pinned clone' 'fail' "dirty checkout; pristine Phase 1 expects a clean tree: $summary"
    return $false
}

function Resolve-UpstreamToolchain {
    param([Parameter(Mandatory = $true)][string]$ClonePath)

    $candidates = @()
    if ($env:NSMBW_TOOLCHAIN) { $candidates += $env:NSMBW_TOOLCHAIN }
    $candidates += (Join-Path (Split-Path -Parent $ClonePath) 'toolchain')
    $candidates += (Join-Path $ClonePath 'Launcher\artifacts\portable-tools')

    foreach ($candidate in $candidates) {
        $full = Get-FullPath $candidate
        if (Test-Path -LiteralPath (Join-Path $full 'CMake\bin\cmake.exe') -PathType Leaf) {
            return $full
        }
    }
    throw "No upstream portable toolchain found. Run Launcher\Prepare-PortableTools.ps1 or set NSMBW_TOOLCHAIN."
}

function Write-Phase1Report {
    param(
        [Parameter(Mandatory = $true)][string]$Result,
        [string]$ErrorMessage = ''
    )

    $script:Stopwatch.Stop()
    $report = [ordered]@{
        schema = 1
        generatedAt = (Get-Date).ToString('o')
        result = $Result
        elapsedSeconds = [Math]::Round($script:Stopwatch.Elapsed.TotalSeconds, 1)
        source = [ordered]@{
            repository = 'WitherBlitz/NSMB-Wii-Multiplayer-Recompilation'
            expectedCommit = $script:ExpectedCommit
            clonePath = $script:NsmbwDir
            dirtyFiles = @($script:CloneDirtyLines)
        }
        environment = $script:EnvironmentInfo
        checks = @($script:Checks)
        artifacts = $script:Artifacts
        manualGate = @(
            'Launch native-build/WiiCompiled.exe on the PC.',
            'Reach the title screen and complete World 1-1.',
            'Create or update a save, exit, relaunch, and confirm the save is still present.',
            'Record the result in ports/nsmbw-xbox/STATUS.md; keep local logs with user paths under work/.'
        )
        error = $ErrorMessage
        privacyNote = 'This local JSON contains absolute local paths. Review/redact it before sharing; keep it under ignored work/ by default.'
    }

    $json = $report | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($script:ReportPath, $json + "`n", (New-Object Text.UTF8Encoding($false)))
    Write-Host ""
    Write-Host "Phase 1 report: $script:ReportPath"
}

# Resolve this port's layout before creating the report location.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$portRoot = Split-Path -Parent $scriptDir
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir '..\..\..')).Path
if (-not $WorkDir) { $WorkDir = Join-Path $portRoot 'work' }
$workRoot = Get-FullPath $WorkDir
$script:NsmbwDir = Join-Path $workRoot 'NSMB-Wii-Multiplayer-Recompilation'
$phaseDir = Join-Path $workRoot 'phase1'
$script:ReportPath = Join-Path $phaseDir 'phase1-report.json'
$script:CloneDirtyLines = @()
$script:Artifacts = [ordered]@{}
$script:EnvironmentInfo = [ordered]@{}
$lockPath = Join-Path $portRoot 'sources.lock.json'
$script:ExpectedCommit = Get-ExpectedCommit -LockPath $lockPath

New-Item -ItemType Directory -Path $phaseDir -Force | Out-Null

try {
    Write-Host 'NSMBW Xbox port - Phase 1 pristine PC baseline'
    Write-Host "Repository: $repoRoot"
    Write-Host "Work area:  $workRoot"

    # --- Basic host prerequisites -------------------------------------------------
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    $cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
    $script:EnvironmentInfo.os = if ($os) { "$($os.Caption) $($os.Version) $($os.OSArchitecture)" } else { 'unknown' }
    $script:EnvironmentInfo.cpu = if ($cpu) { [string]$cpu.Name } else { 'unknown' }
    $script:EnvironmentInfo.powerShell = $PSVersionTable.PSVersion.ToString()

    $preflightFailed = $false

    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Add-Check 'Git' 'fail' 'git was not found on PATH'
        $preflightFailed = $true
    } else {
        $gitVersion = Invoke-Capture -FilePath $git.Source -Arguments @('--version')
        Add-Check 'Git' 'pass' $gitVersion.Text
        $script:EnvironmentInfo.git = $gitVersion.Text
    }

    if (-not (Resolve-Python)) {
        Add-Check 'Python 3' 'fail' 'neither python nor py was found on PATH'
        $preflightFailed = $true
    } else {
        # Use --version rather than a -c snippet: Windows PowerShell 5.1 can
        # mangle embedded quotes when passing arguments to native programs.
        $pythonVersion = Invoke-Capture -FilePath $script:PythonExe `
            -Arguments ($script:PythonPrefix + @('--version'))
        if ($pythonVersion.ExitCode -eq 0 -and $pythonVersion.Text -match '^Python 3\.') {
            $pythonVersionText = $pythonVersion.Text -replace '^Python ', ''
            Add-Check 'Python 3' 'pass' $pythonVersionText
            $script:EnvironmentInfo.python = $pythonVersionText
        } else {
            Add-Check 'Python 3' 'fail' "unexpected version/output: $($pythonVersion.Text)"
            $preflightFailed = $true
        }
    }

    $dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
    if (-not $dotnet) {
        Add-Check '.NET 8 SDK' 'fail' 'dotnet was not found on PATH; install the .NET 8 SDK'
        $preflightFailed = $true
    } else {
        $sdks = Invoke-Capture -FilePath $dotnet.Source -Arguments @('--list-sdks')
        $sdk8 = @($sdks.Output | Where-Object { $_ -match '^8\.' })
        if ($sdks.ExitCode -eq 0 -and $sdk8.Count -gt 0) {
            Add-Check '.NET 8 SDK' 'pass' $sdk8[0]
            $script:EnvironmentInfo.dotnetSdk = $sdk8[0]
        } else {
            Add-Check '.NET 8 SDK' 'fail' 'dotnet is present, but no 8.x SDK was listed'
            $preflightFailed = $true
        }
    }

    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $vswhere -PathType Leaf) {
        $vs = Invoke-Capture -FilePath $vswhere -Arguments @(
            '-latest', '-products', '*', '-version', '[17.0,18.0)',
            '-requires', 'Microsoft.VisualStudio.Workload.Universal',
            '-property', 'installationPath'
        )
        if ($vs.ExitCode -eq 0 -and $vs.Text) {
            Add-Check 'Visual Studio 2022 UWP workload (Phase 2)' 'pass' $vs.Text
            $script:EnvironmentInfo.visualStudio2022Uwp = $vs.Text
        } else {
            Add-Check 'Visual Studio 2022 UWP workload (Phase 2)' 'warn' `
                'not detected by vswhere; not required for Phase 1, required for the Store compile replay'
            $script:EnvironmentInfo.visualStudio2022Uwp = ''
        }
    } else {
        Add-Check 'Visual Studio 2022 UWP workload (Phase 2)' 'warn' `
            'vswhere.exe not found; not required for Phase 1, required later'
        $script:EnvironmentInfo.visualStudio2022Uwp = ''
    }

    $gameFull = Get-FullPath $GameDir
    if (-not (Test-Path -LiteralPath $gameFull -PathType Container)) {
        Add-Check 'Extracted game folder' 'fail' "missing: $gameFull"
        $preflightFailed = $true
        $gameRoot = $null
    } else {
        $gameRoot = Get-GameRoot -Path $gameFull
        if (-not $gameRoot) {
            Add-Check 'Extracted game folder' 'fail' `
                'expected files/ plus sys/boot.bin and sys/main.dol, directly or under DATA/'
            $preflightFailed = $true
        } elseif ((Test-IsUnderPath -Candidate $gameFull -Parent $repoRoot) -and
                  -not (Test-IsUnderPath -Candidate $gameFull -Parent $workRoot)) {
            Add-Check 'Extracted game folder' 'fail' `
                'game data must stay outside tracked repository files; move it outside the repo or under ignored work/'
            $preflightFailed = $true
        } else {
            Add-Check 'Extracted game folder' 'pass' $gameRoot
        }
    }

    $workDriveName = ([IO.Path]::GetPathRoot($workRoot)).Substring(0, 1)
    $drive = Get-PSDrive -Name $workDriveName -ErrorAction SilentlyContinue
    if ($drive -and $drive.Free) {
        $freeGiB = [Math]::Round($drive.Free / 1073741824, 1)
        $script:EnvironmentInfo.freeDiskGiB = $freeGiB
        if ($freeGiB -lt 20) {
            Add-Check 'Free disk space' 'warn' "$freeGiB GiB free; dependencies, generated sources and build output can be large"
        } else {
            Add-Check 'Free disk space' 'pass' "$freeGiB GiB free"
        }
    }

    if ($preflightFailed) {
        throw 'Phase 1 preflight failed. Fix the [fail] checks above, then rerun.'
    }

    # --- Pinned sources -----------------------------------------------------------
    $cloneExists = Test-Path -LiteralPath (Join-Path $script:NsmbwDir '.git')
    $statusBefore = @()
    if ($cloneExists -and $git) {
        $statusBeforeResult = Invoke-Capture -FilePath $git.Source `
            -Arguments @('-C', $script:NsmbwDir, 'status', '--porcelain', '--untracked-files=normal')
        $statusBefore = @($statusBeforeResult.Output | Where-Object { $_ -and $_.Trim() })
    }

    if (-not $CheckOnly -and -not $SkipBootstrap) {
        if ($AllowDirty -and $statusBefore.Count -gt 0) {
            Write-Host 'Skipping bootstrap because -AllowDirty was supplied and bootstrap.py intentionally refuses dirty clones.'
            Add-Check 'Pinned source bootstrap' 'warn' 'skipped for an existing dirty clone (-AllowDirty)'
        } else {
            $bootstrapArgs = @('-WorkDir', $workRoot, '-Audit')
            if ($WithBaseline) { $bootstrapArgs += '-WithBaseline' }
            Invoke-PowerShellFile -Name 'Pinned source bootstrap and Phase 0 audit' `
                -ScriptPath (Join-Path $scriptDir 'bootstrap.ps1') -Arguments $bootstrapArgs `
                -WorkingDirectory $repoRoot
            Add-Check 'Pinned source bootstrap' 'pass' 'bootstrap and read-only audit completed'
        }
    } elseif ($SkipBootstrap) {
        Add-Check 'Pinned source bootstrap' 'warn' 'skipped by request (-SkipBootstrap)'
    }

    if ($CheckOnly -and -not $cloneExists) {
        Add-Check 'NSMBW pinned clone' 'pending' `
            'not bootstrapped yet; run this script without -CheckOnly to clone the pinned sources'
        Add-Check 'Phase 1 execution' 'pending' 'check-only mode; no dependencies prepared and no build run'
        Write-Phase1Report -Result 'check-only-passed-bootstrap-pending'
        exit 0
    }

    if (-not (Test-PinnedClone -ClonePath $script:NsmbwDir -ExpectedCommit $script:ExpectedCommit)) {
        throw 'NSMBW work clone is not in the required pristine pinned state.'
    }

    if ($CheckOnly) {
        Add-Check 'Phase 1 execution' 'pending' 'check-only mode; no dependencies prepared and no build run'
        Write-Phase1Report -Result 'check-only-passed'
        exit 0
    }

    # --- Upstream pinned tools and sources ---------------------------------------
    if (-not $SkipPrepare) {
        Invoke-PowerShellFile -Name 'Prepare pinned portable tools' `
            -ScriptPath (Join-Path $script:NsmbwDir 'Launcher\Prepare-PortableTools.ps1') `
            -WorkingDirectory $script:NsmbwDir

        Invoke-PowerShellFile -Name 'Prepare pinned dependency sources' `
            -ScriptPath (Join-Path $script:NsmbwDir 'Launcher\Prepare-Dependencies.ps1') `
            -Arguments @('-Destination', 'Dependencies') `
            -WorkingDirectory $script:NsmbwDir
    } else {
        Add-Check 'Prepare dependencies/tools' 'warn' 'skipped by request (-SkipPrepare)'
    }

    $toolchain = Resolve-UpstreamToolchain -ClonePath $script:NsmbwDir
    $script:EnvironmentInfo.upstreamToolchain = $toolchain
    Add-Check 'Upstream portable toolchain' 'pass' $toolchain

    if (-not (Test-Path -LiteralPath (Join-Path $script:NsmbwDir 'Dependencies\SDL') -PathType Container)) {
        throw 'Dependencies\SDL is missing. Run without -SkipPrepare so Prepare-Dependencies.ps1 can create it.'
    }
    Add-Check 'Pinned dependency sources' 'pass' 'Dependencies\SDL exists'

    # --- Game-dependent translation inputs ----------------------------------------
    Invoke-PythonChecked -Name 'Validate game and prepare translator inputs (unpack_game.py)' `
        -Arguments @((Join-Path $script:NsmbwDir 'projects\nsmbw\tools\unpack_game.py'), $gameRoot) `
        -WorkingDirectory $script:NsmbwDir

    $translatorGameDir = Join-Path $workRoot 'game'
    foreach ($name in @('main.dol', 'd_profileNP.rel', 'd_basesNP.rel', 'd_enemiesNP.rel', 'd_en_bossNP.rel')) {
        if (-not (Test-Path -LiteralPath (Join-Path $translatorGameDir $name) -PathType Leaf)) {
            throw "unpack_game.py did not produce the expected translator input: $name"
        }
    }
    Add-Check 'Upstream game validation' 'pass' `
        'unpack_game.py accepted the folder as SMNE01 revision 1 with the expected clean main.dol'

    Invoke-PythonChecked -Name 'Prelink boot RELs (prelink_rels.py)' `
        -Arguments @((Join-Path $script:NsmbwDir 'projects\nsmbw\tools\prelink_rels.py')) `
        -WorkingDirectory $script:NsmbwDir

    if (-not (Test-Path -LiteralPath (Join-Path $translatorGameDir 'nsmbw_linked.rel') -PathType Leaf)) {
        throw 'prelink_rels.py did not produce work\game\nsmbw_linked.rel.'
    }
    Add-Check 'REL prelink' 'pass' 'nsmbw_linked.rel generated under ignored work\game'

    # --- Translate, configure and build -------------------------------------------
    Invoke-PowerShellFile -Name 'Translate and build pristine PC product (rebuild-all.ps1)' `
        -ScriptPath (Join-Path $script:NsmbwDir 'projects\nsmbw\tools\rebuild-all.ps1') `
        -Arguments @('-Threads', "$Threads", '-Jobs', "$Jobs") `
        -WorkingDirectory $script:NsmbwDir

    $buildDir = Join-Path $script:NsmbwDir 'native-build'
    $exe = Join-Path $buildDir 'WiiCompiled.exe'
    $shards = Join-Path $script:NsmbwDir 'generated\build_shards\shards.cmake'
    $buildNinja = Join-Path $buildDir 'build.ninja'

    foreach ($required in @($shards, $buildNinja, $exe)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Expected build artifact is missing: $required"
        }
    }

    foreach ($asset in @('dsp_coef.bin', 'initial_pipeline_cache.db')) {
        if (-not (Test-Path -LiteralPath (Join-Path $buildDir $asset) -PathType Leaf)) {
            throw "Expected runtime asset is missing beside the exe: $asset"
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $buildDir 'wii_bootstrap') -PathType Container)) {
        throw 'Expected wii_bootstrap runtime folder is missing beside the exe.'
    }
    Add-Check 'Pristine PC build' 'pass' 'WiiCompiled.exe, build.ninja and shard manifest exist'

    # --- Capture the exact compile commands for the later Store replay ------------
    $ninja = Join-Path $toolchain 'Ninja\ninja.exe'
    if (-not (Test-Path -LiteralPath $ninja -PathType Leaf)) {
        throw "Portable Ninja was not found: $ninja"
    }

    $compdbResult = Invoke-Capture -FilePath $ninja -Arguments @('-C', $buildDir, '-t', 'compdb')
    if ($compdbResult.ExitCode -ne 0 -or -not $compdbResult.Text.TrimStart().StartsWith('[')) {
        throw "ninja -t compdb failed or did not return a JSON array. Output: $($compdbResult.Text)"
    }

    $compdbText = $compdbResult.Text + "`n"
    $compdbBuildPath = Join-Path $buildDir 'compile_commands.json'
    $compdbPhasePath = Join-Path $phaseDir 'compile_commands.json'
    $utf8NoBom = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($compdbBuildPath, $compdbText, $utf8NoBom)
    [IO.File]::WriteAllText($compdbPhasePath, $compdbText, $utf8NoBom)

    $entries = @($compdbText | ConvertFrom-Json)
    if ($entries.Count -eq 0) {
        throw 'compile_commands.json parsed as JSON but contains no entries.'
    }

    $exeItem = Get-Item -LiteralPath $exe
    $script:Artifacts.exe = $exe
    $script:Artifacts.exeBytes = $exeItem.Length
    $script:Artifacts.exeSha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    $script:Artifacts.shardManifest = $shards
    $script:Artifacts.compileCommands = $compdbPhasePath
    $script:Artifacts.compileCommandsEntries = $entries.Count
    $script:Artifacts.compileCommandsSha256 = `
        (Get-FileHash -LiteralPath $compdbPhasePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $script:Artifacts.buildLog = Join-Path $buildDir 'logs\rebuild-build.log'
    $script:Artifacts.configureLog = Join-Path $buildDir 'logs\configure.log'

    Add-Check 'Compilation database' 'pass' "$($entries.Count) entries captured at $compdbPhasePath"

    # --- Optional convenience for the manual smoke test ----------------------------
    if ($CreateGameLink) {
        $gameLink = Join-Path $buildDir 'game'
        if (Test-Path -LiteralPath $gameLink) {
            Add-Check 'PC game link' 'warn' "native-build\game already exists; left untouched"
        } else {
            New-Item -ItemType Junction -Path $gameLink -Value $gameFull | Out-Null
            Add-Check 'PC game link' 'pass' "native-build\game -> $gameFull"
        }
    }

    if ($Launch) {
        $process = Start-Process -FilePath $exe -WorkingDirectory $buildDir -PassThru
        $script:Artifacts.launchedProcessId = $process.Id
        Add-Check 'Manual smoke test launch' 'pending' "started WiiCompiled.exe (PID $($process.Id)); gameplay verification is manual"
    } else {
        Add-Check 'Manual smoke test' 'pending' 'title -> World 1-1 -> save/reload still has to be played and recorded'
    }

    Write-Phase1Report -Result 'build-complete-manual-smoke-pending'
    Write-Host ""
    Write-Host 'Phase 1 build completed. Manual gate still required:'
    Write-Host "  1. Run: $exe"
    Write-Host '  2. Reach the title screen, complete World 1-1, save, exit and relaunch.'
    Write-Host '  3. Report pass/fail plus the tail of the relevant log if it fails.'
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Phase1Report -Result 'failed' -ErrorMessage $message
    Write-Host ""
    Write-Host "Phase 1 failed: $message" -ForegroundColor Red
    Write-Host 'Useful logs are under the NSMBW clone native-build\logs and in the phase1 report.'
    exit 1
}
