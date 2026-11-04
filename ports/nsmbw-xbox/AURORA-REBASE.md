# Aurora rebase plan — from the proven Mario Kart patch to NSMBW’s fork

## Why this document exists

jajdp’s `patches/aurora-uwp.patch` is the most valuable artifact in this port: it is the Aurora half of a WiiCompiled-family game that actually boots inside an Xbox AppContainer. It is also **not applicable as a patch** to our tree. On 2026-11-04, `git apply --check --directory=aurora-main` (read-only) failed against all three Aurora trees we cloned:

| Target tree | Result |
|---|---|
| NSMBW `v0.3.1` vendored `aurora-main` | fails |
| WiiCompiled `v0.2.31` vendored `aurora-main` (the recipe’s named baseline) | fails |
| Current WiiCompiled `aurora-main` submodule `33067e34…` | fails |

The patch preimage expects, for example, centralized `_aurora_dependency_version(...)` declarations and newer SDL/nod pins that none of those trees have in the same form. Conclusion: **the patch is a semantic specification from a fourth Aurora snapshot.** Force-applying it would create a tree that neither matches upstream NSMBW nor the proven port. We re-implement its intent, file by file, on NSMBW’s Aurora — keeping every change behind `AURORA_WINDOWS_STORE` so the PC build remains the control experiment.

Distances that justify rebasing *forward from NSMBW* rather than swapping Aurora wholesale (name-only `diff -qr` counts):

- NSMBW Aurora vs WiiCompiled `v0.2.31` Aurora: **69** differing paths.
- NSMBW Aurora vs current WiiCompiled Aurora: **293** differing paths.

NSMBW’s fork carries game-specific renderer work we must preserve (among others: staging-buffer helpers, EFB RAM copy/encode paths, frame interpolation/dynamic-aspect integration, texture replacement/dump plumbing, and its pipeline-cache behavior). Replacing `aurora-main` with another snapshot would trade one rebase for a larger, gameplay-affecting one.

## The 22 recipe files, and what we do with each

Hunk/add/delete counts below come from the generated audit (`reports/2026-11-04-phase0-audit.md`). “Intent” summarizes the recipe’s own docs plus the patched file’s role; during implementation each hunk is read again against the NSMBW file before writing our version. **Skip** means “not needed for the first couch-only package,” not “delete upstream code.”

| Aurora file | Recipe intent (high level) | NSMBW rebase action |
|---|---|---|
| `.gitignore` | Ignore the UWP build dir | Mirror in our port `.gitignore` only; no upstream change needed |
| `CMakeLists.txt` | Detect WindowsStore, default tests off there, add `uwp_dep` provider choices | **Re-implement first.** NSMBW hardcodes Dawn `v20260603.191052`, SDL 3.4, nod alpha.8 — keep those pins; add Store detection and provider enum values without importing the newer version-macro refactor |
| `cmake/AuroraUwpDep.cmake` (new) | Locate/fetch the pinned UWP prebuilt bundle and expose imported targets | **Landed in patch `0002`, fail closed with two explicit local roots:** `AURORA_UWP_DEP_SOURCE_DIR` for the main Dawn/nod/libpng/zlib/DXC/libuwp checkout at `6ba4aad1...`, and `AURORA_UWP_SDL_SOURCE_DIR` for the separate true-UWP SDL checkout at its parent `ae39aa00...`. It performs no network fetch or desktop-provider fallback; it verifies Git HEADs when roots are checkouts, checks required files, rejects using one folder for both roots, and defines `aurora::uwp_dep` from the main bundle's `LIBUWP`. Layout/licences/hashes/PE imports were inspected 2026-11-04; Windows header/link verification is still required |
| `cmake/AuroraDawnProvider.cmake` | `uwp_dep` Dawn/WebGPU imported target; refuse desktop Dawn on Store | Re-implement against NSMBW’s provider structure. Xbox gets Dawn’s D3D12 backend only; no Vulkan define in the Store compile pass |
| `cmake/AuroraSDL3Provider.cmake` | `uwp_dep` SDL3 imported target | Re-implement from `AURORA_UWP_SDL_SOURCE_DIR` only. This is now PE-verified, not just recipe folklore: the main pin’s SDL 3.4.10 DLL imports desktop `MSVCP140.dll`/`VCRUNTIME140.dll`, while `ae39aa00...` provides SDL 3.4.8 headers/import lib/DLL importing the `_APP` runtimes. Headers, import library and packaged DLL must all come from that separate checkout |
| `cmake/AuroraNodProvider.cmake` | `uwp_dep` nod imported target | Re-implement only if the linked product actually pulls Aurora’s DVD/nod objects; otherwise keep provider parity but do not package an unused DLL |
| `cmake/AuroraCopyRuntimeDLLs.cmake` | Copy UWP bundle DLLs beside desktop-style outputs | Adapt to our packaging staging step instead of post-build copying into a PC output folder |
| `cmake/aurora_core.cmake` | Core target compile/link adjustments for Store | Read hunk-by-hunk; apply the minimum defines/links. Preserve NSMBW’s `frame_interpolation.cpp` source-property handling in the runtime CMake |
| `extern/CMakeLists.txt` | Use bundle zlib/libpng etc.; avoid building desktop-only externs for Store | Re-implement the “don’t duplicate symbols” rule: objects already provided by the UWP bundle are excluded from our compile/link sets, exactly as the recipe’s linker does |
| `examples/simple.c`, `tests/CMakeLists.txt` | Keep examples/tests from breaking Store configure | **Skip for v1:** examples/tests stay off in the Store lane. Revisit only if we want an Aurora-only smoke app |
| `lib/aurora.cpp` | Init/path adjustments for Store | Re-implement on NSMBW’s version, which already falls back to `SDL_GetPrefPath` for user/cache paths. The runtime passes explicit LocalState-based paths anyway (see `overlay/README.md`) |
| `lib/card/CardGciFolder.cpp`, `lib/card/CardRawFile.cpp`, `lib/card/File.cpp`, `lib/card/Util.cpp` | Card file/path portability under AppContainer | Small, surgical ports. NSMBW is a Wii NAND-save game first; keep card changes compile-only correct and do not redesign save storage around GameCube cards |
| `lib/card/DolphinCardPath.cpp` | Replace Documents/registry lookup on Store | **Replace, don’t enable the legacy branch.** As inspected, NSMBW’s file still contains an old `WINDOWS_STORE` C++/CX-flavored branch that does not look like a maintained build path next to the desktop wide-string code below it. Use the same `SDL_GetPrefPath` idiom as the rest of the port |
| `lib/dolphin/pad/pad.cpp` | Pad-layer Store adjustments (small) | Read the four-line delta against NSMBW’s heavily evolved pad/input code; preserve NSMBW’s virtual-remote and motion mappings |
| `lib/input.cpp` | Input init under the UWP SDL build | Combine with the later script change below: no `SDL_INIT_HAPTIC` in the Store lane until the chosen SDL fork proves rumble on hardware |
| `lib/main.cpp` | Aurora’s standalone entry shim | **Mostly skip:** the game uses the runtime’s `RuntimeMain`, and Aurora’s own `main` object is excluded at link (the recipe does the same). Keep it compiling; don’t let it provide a second entry point |
| `lib/system_info.cpp` | Store-appropriate system information implementation (largest code hunk set) | Port carefully and keep it boring: static, truthful values for an x64 Series-class console are better than clever desktop probes. Anything the game logic branches on must be traced to a caller first |
| `lib/webgpu/gpu.cpp` | Dawn device/surface toggles for Store/D3D12 | Port with the CoreWindow change below as one reviewed unit. Add a kill-switch config for pipeline-cache seeding: cached D3D12 pipeline blobs are a known Xbox Dev Mode device-removal suspect in our earlier research, so first boot must be testable with seeding off |

## The seven later changes (`tools/parche-aurora.py` in the recipe)

These are the “make it actually boot” fixes. Our audit checks their anchors by short API markers; all seven concepts map onto files that exist in NSMBW’s Aurora:

1. `lib/logging.cpp` — Store-guard the fatal `MessageBoxA`; the log file is the UI.
2–5. `lib/window.cpp` — Store-guard the Win32 `WNDPROC` hook state, its native-client-size fast path, and hook install/remove. NSMBW’s window layer still installs an HWND hook on `_WIN32`; on UWP there is no HWND to hook.
6. `lib/dawn/BackendBinding.cpp` — add the **CoreWindow** surface branch before the desktop HWND branch. NSMBW currently branches Android → Win32 HWND → Linux; the UWP SDL window property must feed Dawn’s Windows CoreWindow surface descriptor instead. This is the single most important graphics change in the port.
7. `lib/input.cpp` — initialize joystick/gamepad without haptics in the Store lane.

## Rebase order (each step keeps the PC build green)

| Patch | Scope | Gate before moving on |
|---|---|---|
| `0001-aurora-store-detection` ✅ *written 2026-11-04* | `AURORA_WINDOWS_STORE` detection (CMake `WindowsStore` system name), `AURORA_BUILD_TESTS` defaulting off on Store, and the `aurora_core` PUBLIC compile definition. No providers, no code behavior change | `git apply --check` on a clean pinned checkout ✅ (verified; test tree restored). Desktop configure/build unchanged — **pending** the Phase 1 PC gate |
| `0002-aurora-uwp-dep-providers` ✅ *written after `0001`* | Provider enum/defaults + new local-only `AuroraUwpDep.cmake` + Dawn/SDL/nod `uwp_dep` branches. SDL root is separate from the main Dawn/nod/libuwp root; Git pins, required files, and same-folder misuse are checked and desktop providers are rejected in the Store lane | Series apply ✅ on a clean pinned clone. Synthetic CMake harnesses ✅: missing SDL root fails with our message; layout fixtures force all enabled providers to `uwp_dep` and create the expected imported targets. Real Windows Store configure/link and the desktop PC rebuild gate remain pending |
| `0003-aurora-extern-link-hygiene` | Extern/core adjustments; no duplicate zlib/libpng/libusb objects in the Store lane | Store compile-check object list has no known duplicate-symbol providers |
| `0004-aurora-paths` | `lib/aurora.cpp` + card path files via pref-path/LocalState idiom | PC run still finds its existing user data; no `SHGetKnownFolderPath` remains in Aurora Store compile set |
| `0005-aurora-window-surface-input` | Window hook guards, logging guard, haptics guard, CoreWindow surface | Desktop window/resize behavior unchanged; Store compile set has no HWND hook or `SDL_INIT_HAPTIC` |
| `0006-aurora-system-info-gpu` | `system_info.cpp` + `webgpu/gpu.cpp` minimum Store deltas; pipeline-seed kill switch | Caller-traced values only; first-boot test plan can disable pipeline seeding without a rebuild if config plumbing allows |


## Explicit non-goals for the Aurora lane

- No Vulkan/Metal/OpenGL work for Xbox; Dawn on D3D12 is the only v1 graphics path (D3D11 remains a *config* fallback only if the bundled Dawn proves it works — not a second renderer project).
- No wholesale Aurora upgrade to the current WiiCompiled submodule during this port.
- No C++/CX resurrection. New WinRT-facing code, where unavoidable, stays in our overlay/entry shim, not sprinkled through Aurora.
- No texture dumps/replacements, screenshot tooling, or debug overlays in the first package beyond what the log file already gives us.
