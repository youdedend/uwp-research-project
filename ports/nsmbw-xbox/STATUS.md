# Status ledger — NSMBW Xbox Series S port

Last updated: **2026-11-04** · Branch: `arena/edfdf068-uwp-research-project` · Phase: **1 — pristine PC baseline ready to run on Windows; Aurora patches `0001`-`0003` written**

## Verified so far

| Fact | Evidence |
|---|---|
| Primary source pinned | `WitherBlitz/NSMB-Wii-Multiplayer-Recompilation` tag `v0.3.1`, commit `aa7cf830837358d241e734e94741405c7c824ab2` (GPL-3.0), cloned and inspected in this session |
| Recipe pinned | `jajdp/retro-rewind-xbox` commit `75e96a662ebb97a937fd27f474d0575669dcd4a9` (MIT): 22-file Aurora patch, 7-change Aurora script, two-pass compile, `ld.lld` link, manifest, packaging script |
| Recipe hardware truth | Upstream reports Series X testing at 58 FPS and states a Series S was never tried. We must not quote its numbers as Series S expectations |
| Recipe Aurora patch shape | 22 files; providers/CMake/card paths/input/GX surface changes behind `AURORA_WINDOWS_STORE` (file/hunk inventory in `reports/2026-11-04-phase0-audit.md`) |
| Blind patch application is a dead end | `git apply --check --directory=aurora-main` fails against NSMBW `v0.3.1`. It also fails against WiiCompiled `v0.2.31` and the inspected current WiiCompiled Aurora submodule, so the patch preimage is yet another Aurora snapshot. **Do not retry with `--reject`/`--3way` as the strategy; rebase semantically** |
| NSMBW Aurora distance | Name-only diff: **69** differing paths vs WiiCompiled `v0.2.31` Aurora; **293** vs current WiiCompiled Aurora submodule (`33067e34…`). NSMBW’s fork is v0.2.31-era plus its own renderer/input work |
| NSMBW already has useful seams | `RuntimeMain(argc, argv)` is separate from `main()`; `SDL_GetPrefPath` is already used in Aurora/card paths; runtime names D3D11/D3D12/Vulkan backends; a host-suspend module exists (behavior still to audit) |
| NSMBW desktop blockers confirmed by symbol scan | Known-folder paths, `_pipe` transcript, `MessageBox`, DbgHelp, plain fibers, vectored handlers, Schannel, Discord named pipe, COM folder picker, updater/netplay `CreateProcess`, HWND hooks, Crypto++ `stdext`, SDL haptics init. Exact files/lines: generated audit report |
| Exact game + target environment confirmed | On 2026-11-04 the user confirmed they have the exact **USA `SMNE01` revision 1** copy, a **Series S in Developer Mode**, and a **Windows PC with Visual Studio 2022**. Recorded in `sources.lock.json`; upstream `unpack_game.py` still performs the technical title/revision/`main.dol` hash check in Phase 1 |
| Clean-tree build order corrected | `runtime/CMakeLists.txt` fails without `generated/build_shards/shards.cmake`, so a clean PC build must run `unpack_game.py` -> `prelink_rels.py` -> `rebuild-all.ps1` before configure. The new `tools/run-phase1-pc.ps1` encodes the full upstream order, checks Git/Python 3/.NET 8, and captures `compile_commands.json`; it **has not yet been run on Windows** |
| First Aurora patches written | `patches/0001-aurora-store-detection.patch` (+18/-1) adds Store detection, the `AURORA_BUILD_TESTS` gate, and PUBLIC `AURORA_WINDOWS_STORE=1`. `patches/0002-aurora-uwp-dep-providers.patch` (+287/-10) adds the local-only fail-closed two-root `AuroraUwpDep.cmake` and Dawn/SDL/nod `uwp_dep` branches. `patches/0003-aurora-extern-link-hygiene.patch` (+122/-2) bundle-imports zlib/libpng fail-closed, forces vendored SDL/libusb off in the Store lane, defines `SQLITE_OS_WINRT=1`, makes Tracy headers-only there, links `aurora::uwp_dep` PUBLIC from `aurora_core`, and makes the Windows system-info libs Store-aware. Clean-clone series apply (`0001→0002→0003`) and `git diff --check` pass; synthetic CMake harnesses verified the missing-bundle failures and the Dawn/SDL/nod/`LIBUWP`/zlib/libpng/Tracy/core target logic. Their desktop PC rebuild and real Windows Store configure/link gates are still pending |
| UWP dependency pins sharpened | `XboxEmulationHub/uwp-dep@6ba4aad1...` (branch `dusklight`) supplies the candidate Dawn/nod/libpng/zlib/DXC/libuwp bundle; layout, component licences, selected SHA-256 hashes and PE imports were inspected. Its SDL 3.4.10 DLL imports desktop MSVC runtimes and is rejected. Use the separate parent pin `ae39aa00...` for SDL 3.4.8: its DLL imports the `_APP` runtimes, matching the recipe's separate `uwp-dep-sdl` folder. Windows header/link verification remains Phase 2 |
| GitHub Actions test lane added | `.github/workflows/ci.yml` validates all committed Python/PowerShell/config/docs, parses every `.ps1` with Windows PowerShell, performs the pinned bootstrap+audit on Ubuntu and Windows, applies patches `0001`-`0003` in series to a disposable clone, and runs Phase 1 `CheckOnly` on a Windows runner against a layout-only fixture. Hosted CI still does **not** run the real game translation/build because the owner's extracted game is not (and must not be) in GitHub |

## Not done / not claimed

- [ ] Upstream PC source build and manual PC smoke test with the real game on the user's Windows machine (neither this Linux sandbox nor GitHub-hosted Actions has the owner's game input; hosted CI covers `CheckOnly`, pinned bootstrap/audit, scripting, and patch application).
- [ ] Desktop rebuild with patches `0001`-`0003` applied; CMake/Ninja build verification of the patched Aurora is still pending (the synthetic harnesses only tested module/target logic, not Windows headers or compilation).
- [ ] Windows-side header/API/link verification of the pinned UWP prebuilts (metadata, hashes and PE imports inspected; no Store link has run yet).
- [ ] Aurora patches `0004`-`0006`, the runtime overlay code, a Store-environment compile, an AppContainer link, or a package.
- [ ] Any built Xbox `.exe`, `.msix`, console install, screenshot, FPS number, memory figure, or Series S save test.

## Current blockers, in order

1. **PC green-build gate (baseline):** run the pristine source build and manual PC smoke test. The Xbox compile pass consumes that build’s `compile_commands.json`; without it there is nothing trustworthy to recompile.
2. **Aurora version drift (engineering):** implement the recipe’s surface/path changes directly on NSMBW’s Aurora instead of applying its patch. Patches `0001` (detection), `0002` (fail-closed `uwp_dep` providers), and `0003` (extern/link hygiene) now exist; `0004` (pref/card paths) is next, with the real duplicate-object/link check gated on the green compile database and the verified two-commit UWP dependency split.
3. **UWP prebuilt link gate:** do not use the main bundle’s desktop-linked SDL. Confirm Dawn/nod/SDL header and import-library compatibility during the Store compile/link; keep all third-party binaries local under ignored `work/`.
4. **Series S unknowns (hardware):** 5 GB UWP game memory envelope, weaker GPU than the recipe’s Series X, shader-compile stalls, and Dev Mode suspend/reset behavior must be measured standalone (no debugger).

## Immediate next actions

1. Keep the GitHub Actions workflow green on this branch; use its uploaded bootstrap/audit/CheckOnly artifacts when diagnosing script or pin regressions.
2. On the Windows PC, from the repo root, run the pristine baseline (replace the game path):
   `powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\run-phase1-pc.ps1 -GameDir "D:\Path\To\Extracted\SMNE01-rev1" -WithBaseline -CreateGameLink`
3. Play that PC build: title → World 1-1 → save → exit/relaunch → save persists. Keep `work\phase1\compile_commands.json` and `phase1-report.json`; report the result and, on failure, the exact failing step plus the relevant log tail. Do not upload game files or generated game code.
4. Apply patches `0001`-`0003` in the work clone and repeat the desktop build as their no-behaviour-change gate.
5. Use the green compilation database to verify `0002`-`0003` against the real UWP prebuilts, write `0004` (pref/card paths), and produce the first Store-environment error histogram; land the log-first overlay before expecting anything visible on Xbox.

## Difficulty note

Provisional **D3 (hard)** from the research docs stands: complete public source and a proven sibling port help, but NSMBW has no public UWP build, its Aurora/runtime have diverged, and Series S is unmeasured. Re-rate only after the Phase 2 Store-environment compile histogram exists.
