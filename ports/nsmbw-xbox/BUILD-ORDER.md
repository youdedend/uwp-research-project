# Build order — NSMBW Xbox Series S UWP port

Runtime-first, like the research docs prescribe: prove the PC build, rebase Aurora, make failures visible, compile in the Store environment, link as an AppContainer binary, package, then measure on the Series S. **Do not skip a gate to “just try it on the console.”** On Xbox, an unlogged failure and a missing DLL look identical: splash screen, then Home.

> Commands below marked **[Upstream]** are taken from the pinned repos’ own docs/scripts as inspected on 2026-11-04. Commands marked **[This port]** are ours. Nothing here has been executed on a Windows PC or console yet in this project; treat every first run as an experiment and record the result in `STATUS.md`.

## Phase 0 — Pin and audit (complete)

1. **[This port]** Clone the pinned trees into ignored `work/` and generate the audit:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\bootstrap.ps1 -WithBaseline -Audit
   ```

2. **[This port]** Re-run the audit after every patch series; the desktop-API counts in the *Store compile set* must trend to zero for the blocking categories. The audit never modifies the trees.

**Gate G0:** `sources.lock.json` commits match (`--check` passes) and the team agrees the Aurora work is a rebase, not a patch application.

## Phase 1 — Green PC build (the control experiment)

Confirmed on 2026-11-04: the exact **USA `SMNE01` rev 1** copy is available, the target Series S is in Developer Mode, and a Windows PC with Visual Studio 2022 is available. Prepare the extracted game folder outside this repo (or under ignored `work/`) following upstream’s own player/build documentation. How a disc is dumped/decrypted is out of scope here. The folder passed below must contain `files\` plus `sys\boot.bin`/`sys\main.dol`, either directly or under a `DATA\` child.

Additional PC prerequisites upstream requires: **Git, Python 3, and the .NET 8 SDK**. Visual Studio is not what configures this PC baseline—the source build uses upstream’s pinned portable llvm-mingw/CMake/Ninja—but VS 2022 becomes essential in Phase 2.

### Recommended: run the Phase 1 wrapper

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\run-phase1-pc.ps1 `
  -GameDir "D:\Path\To\Extracted\SMNE01-rev1" `
  -WithBaseline -CreateGameLink
```

Replace `D:\Path\To\Extracted\SMNE01-rev1` with your extracted folder. The first successful translation/build can take a long time and downloads upstream’s pinned portable tools/dependency sources. The wrapper refuses a dirty NSMBW checkout unless `-AllowDirty` is explicitly supplied, applies **no Xbox patches**, and writes the PC build plus `work\phase1\compile_commands.json` and a local `phase1-report.json` under ignored `work/`. `-CreateGameLink` only creates a directory junction at `native-build\game`; it does not copy game data. Use `-CheckOnly` first for a prerequisite-only report, or add `-Launch` to start the built exe immediately. Record the run with [`reports/phase1-pc-report.template.md`](reports/phase1-pc-report.template.md); it lists exactly which hashes, checks, manual results, and log tails are useful to bring back.

### Manual equivalent (the order matters)

Do **not** run `configure-native.ps1` first on a clean tree. `runtime/CMakeLists.txt` requires `generated\build_shards\shards.cmake`, and only the translator steps in `rebuild-all.ps1` create it.

1. **[This port]** Bootstrap the pinned clean trees:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\bootstrap.ps1 -WithBaseline -Audit
   ```

2. **[Upstream]** Inside `ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation`, prepare the pinned portable toolchain and dependency sources (the native configure script later refuses to run without `Dependencies\SDL`):

   ```powershell
   powershell -ExecutionPolicy Bypass -File Launcher\Prepare-PortableTools.ps1
   powershell -ExecutionPolicy Bypass -File Launcher\Prepare-Dependencies.ps1 -Destination Dependencies
   ```

3. **[Upstream]** Validate the game folder and create the translator inputs. `unpack_game.py` checks `SMNE01`, disc-version byte `0x01`, and the expected clean `main.dol` SHA-1, then writes `..\game\main.dol` plus the four boot RELs; `prelink_rels.py` writes the synthetic linked REL the translator consumes:

   ```powershell
   python projects\nsmbw\tools\unpack_game.py "D:\Path\To\Extracted\SMNE01-rev1"
   python projects\nsmbw\tools\prelink_rels.py
   ```

4. **[Upstream]** Run the full translator/build pipeline. It builds the .NET translator, runs `translate-recursive` -> `emit-base-manifest` -> `generate-data-init` -> `emit-build-shards`, configures `native-build` if `build.ninja` is absent (base `NSMBW_GAME_ID=SMNE01`, canonical `Launcher\NativeBuildFlags.ps1` flags), then builds target `WiiCompiled`:

   ```powershell
   powershell -ExecutionPolicy Bypass -File projects\nsmbw\tools\rebuild-all.ps1
   ```

   Expected outputs include `generated\build_shards\shards.cmake`, `native-build\build.ninja`, `native-build\WiiCompiled.exe`, and the runtime assets copied beside the executable (`dsp_coef.bin`, `initial_pipeline_cache.db`, `wii_bootstrap\`). Useful logs are under `native-build\logs\`.

5. **[Manual gate]** Play the PC build before porting it (title -> World 1-1 -> save -> exit/relaunch -> save persists). A port of a broken PC build is two debugging problems wearing a trench coat.

6. **[This port]** Preserve the exact compilation database from that green build. The base build directory is literally `native-build`; `NativeBuildFlags.ps1` does not ask CMake to emit the database, so capture Ninja’s own view:

   ```powershell
   . projects\nsmbw\tools\paths.ps1
   $build = Get-NsmbwBuildDirectory 'native-build'
   $ninja = Join-Path (Get-NsmbwToolchain) 'Ninja\ninja.exe'
   & $ninja -C $build -t compdb | Set-Content -LiteralPath (Join-Path $build 'compile_commands.json') -Encoding utf8
   ```

   Do not substitute a random system Ninja/CMake/clang: the whole point is replaying *this* build. Keep the database under ignored `work/` unless you have reviewed the local paths it contains.

**Gate G1:** the pristine PC build exits 0, plays World 1-1, saves/reloads, and `compile_commands.json` is captured. Record PC specs, build time, compile-command count/hash, and the manual result in `STATUS.md`. Only then apply `patches/0001-aurora-store-detection.patch` and repeat the desktop build as its no-behaviour-change gate.

## Phase 2 — Aurora rebase + Store compile histogram

1. **[This port]** Land `patches/0001…0006` in the order given in [`AURORA-REBASE.md`](AURORA-REBASE.md), re-running the Phase 1 PC build after each patch. PC behavior must not change with `AURORA_WINDOWS_STORE` off.
2. **[This port]** Clone the UWP prebuilts only into ignored `work/`, using the *two* pins now recorded in `sources.lock.json`: main Dawn/nod/libuwp bundle `XboxEmulationHub/uwp-dep@6ba4aad1…`, and a separate SDL checkout at its parent `ae39aa00…`. Metadata/layout/component licences, selected SHA-256 hashes and PE import names were inspected on 2026-11-04. The `6ba4aad1` SDL is explicitly rejected: despite 3.4.10 headers, its DLL imports desktop `MSVCP140.dll`/`VCRUNTIME140.dll`; the `ae39aa00` SDL 3.4.8 DLL imports the `_APP` runtimes. Before linking, still verify header/API compatibility and the actual import list on Windows with `dumpbin /dependents` or equivalent.
3. **[Upstream recipe, adapted]** Compile in Visual Studio’s **store** environment (`vcvarsall x64 store`), replaying `compile_commands.json` with the MSVC-ABI clang from the portable toolchain, `WINAPI_FAMILY_APP`, UWP-bundle headers first, PCH stripped, Vulkan define removed. Run the pass **twice** (runtime/generated/Aurora, then deps) — in the recipe the second pass is what brings ImGui, and skipping it presents as ~20 unresolved symbols at link.
4. **[This port]** Save the compiler’s error histogram per group (`runtime`, `generated`, `aurora`, `deps`, `third_party`). This histogram, not optimism, decides whether the rating stays D3.

**Gate G2:** Every translation unit in the single NSMBW product compiles in the Store environment, or the remaining failures are enumerated with owners in `STATUS.md`. (NSMBW builds one product, so the recipe’s two-product `indirect_dispatch` collision should not apply — but the link object list must still come from the PC build’s real link line, not from globbing.)

## Phase 3 — Runtime overlay (log first, then life support)

Implement in this order (design details in [`overlay/README.md`](overlay/README.md)):

1. **Observability:** before SDL/Aurora init, redirect unbuffered `stdout`/`stderr` to `LocalState\NSMBW\Logs\uwp-console.txt`; keep the runtime’s own log beside it.
2. **Paths:** application data → `LocalState\NSMBW\`; game data → fixed sibling contract `LocalState\GameAssets\DATA` via `Config.toml` (`dvd_root = "../GameAssets/DATA"`); package-root runtime assets (`dsp_coef.bin`, `initial_pipeline_cache.db`, `wii_bootstrap\`) stay read-only beside the exe.
3. **Entry:** new WinRT/SDL entry shim calling the existing `RuntimeMain(argc, argv)`; desktop `main`, console transcript pipes, `MessageBox` fatals and DbgHelp are compiled out, not stubbed with dialogs.
4. **Life support:** `Ex` fiber variants; hand-declared vectored-exception handlers kept in one auditable place; CPU-baseline/compat-handoff reduced to “log and continue on the known console CPU.”
5. **Amputations (v1):** self-updater, COM folder picker, Discord IPC, Schannel guest TLS (stubbed), netplay process relaunch — excluded/failed-closed behind the port define, with the PC paths untouched.

**Gate G3:** A Store-environment build with the overlay links far enough that remaining errors are *only* link/package issues, and the binary contains no imports from the audit’s blocking categories.

## Phase 4 — Link and package

1. **[Upstream recipe, adapted]** Archive Aurora/deps objects into static libs (so the linker pulls only what the runtime uses, as on PC), then link with `ld.lld` in link mode. The two non-negotiable flags from the recipe: `/appcontainer` and **`/subsystem:windows,10.0`** (lld’s default 6.0 gives the silent activation failure `0x8027025B`; the same code also fires for a missing VCLibs dependency, so check both).
2. **[This port]** Stage the package from [`package/README.md`](package/README.md): renamed exe (`NSMBW.exe`), UWP DLL set, runtime assets, manifest, your own placeholder tiles. **No game data inside the package.**
3. **[Upstream/Microsoft tooling]** Pack and sign with the Windows SDK (`makeappx pack`, `signtool sign`) using *your* certificate whose subject exactly matches the manifest `Publisher`; bump the manifest `Version` for every new package or the console will not replace the old one.
4. **[This port]** Install via Xbox Device Portal, launch once to create `LocalState`, then upload your prepared game folder to `LocalState\GameAssets\DATA` and the `Config.toml` to `LocalState\NSMBW\` through the portal’s file explorer. Download the logs the same way after every test.

**Gate G4:** Package installs and reaches the title screen on the Series S *standalone* (no debugger — a debugger waives the memory limit and hides the real failure mode).

## Phase 5 — Series S acceptance (v1)

Run in order; stop and fix at the first failure. Record every number in `STATUS.md` — Series S data for this runtime family does not exist anywhere else yet.

| # | Test | Pass condition |
|---|---|---|
| 1 | Cold boot ×3 | Title screen every time; log shows the D3D12/Dawn backend and no fatal lines |
| 2 | World 1-1 complete | No missing textures severe enough to block play; note shader-compile stalls separately from steady-state FPS |
| 3 | Save → quit to Home → relaunch | Save persists (proves the `LocalState` NAND path end-to-end) |
| 4 | Two controllers, couch co-op join | Player 2 joins, rumble absence is acceptable in v1, disconnect/reconnect does not hang input |
| 5 | 30-minute standalone soak | No crash, no device-removed, memory stable in the log; if it dies, repeat with pipeline-cache seeding disabled before theorizing |
| 6 | Suspend/Home resume probe | *Expected to restart the game* (unsolved in the recipe). Pass = it restarts cleanly and the save survives; anything better is a bonus to document |
| 7 | Resolution/FPS sweep | Try `resolution_multiplier` 1.0 first; only then higher. Series S GPU headroom is measured, never assumed from Series X numbers |

**Gate G5 (= v1 done):** tests 1–5 pass on the Series S. Only then consider Phase 6 candidates: LAN netplay without process relaunch, removable-storage game data, rumble, settings overlay polish, suspend state save/restore.
