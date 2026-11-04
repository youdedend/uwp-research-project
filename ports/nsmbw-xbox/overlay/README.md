# Runtime overlay design (our new code lives here)

The overlay is the small amount of *new* code this port adds beside the upstream runtime, plus the guarded edits inside it. Design rules:

1. **One define:** runtime changes sit behind `NSMBW_UWP` (Aurora keeps its own `AURORA_WINDOWS_STORE`). The same tree must always build and play on PC with both defines off.
2. **Log first:** nothing is debuggable on the console until output reaches a file. Observability lands before graphics.
3. **Exclude, don’t amputate upstream:** desktop features are compiled out or fail closed under the define; PC code paths are not deleted.
4. **No copied recipe runtime code:** the jajdp repo (MIT) deliberately ships *descriptions* of its twelve WiiCompiled runtime changes, not a runtime patch. We implement the NSMBW equivalents ourselves against GPL-3.0 upstream code and keep our patches GPL-compatible.

## Entry point

NSMBW already splits startup the right way: `runtime/src/main.cpp` ends with a thin `main()` (or Android `SDL_main`) forwarding to `RuntimeMain(argc, argv)`. The Xbox lane adds **one new translation unit** (working name `runtime/src/uwp_main.cpp` in the overlay tree) that:

- provides the WinRT/CoreApplication-facing entry the chosen UWP SDL/libuwp bridge expects — **exact signature to be copied from the pinned bundle’s headers at implementation time, not invented here**;
- redirects `stdout`/`stderr` (unbuffered) into `LocalState\NSMBW\Logs\uwp-console.txt` *before* any SDL/Aurora initialization;
- then calls `RuntimeMain` with a synthetic `argv` (`argv[0]` = executable name, no desktop flags).

The desktop `main()` object and Aurora’s own `lib/main.cpp` object are both excluded from the Xbox link (two entry points is the recipe’s classic silent-exit trap family). Until the bundle headers are in hand and license-verified, this file is a design, not code — writing WinRT entry code from memory is how ports lose a weekend.

## The twelve recipe changes, mapped to NSMBW

| # | Recipe problem (WiiCompiled file) | NSMBW equivalent & v1 treatment |
|---|---|---|
| 1 | `runtime_config.h` asks `SHGetKnownFolderPath` for user data | Same file asks for Documents (`MarioWiiSaveData`) then LocalAppData. Under `NSMBW_UWP`, application data = `SDL_GetPrefPath` result for the app (package `LocalState`); skip the “adopt earlier portable UserData” desktop migration entirely |
| 2 | `host_platform.cpp` resolves that folder (2 changes) | `runtime/src/platform/host_platform.cpp::ApplicationDataDirectory` gets the same Store branch; `ExecutableDirectory()` must keep working because runtime assets are read from the read-only package root |
| 3 | `main.cpp` bulk (14 changes): WinRT entry, no console/`_pipe`, no `MessageBox`, no DbgHelp, log to file, `SDL_Init` without haptics | NSMBW’s `main.cpp` has all of these plus netplay/updater hooks. Transcript-pipe machinery, DbgHelp symbolication and fatal popups compile out; the *log file* behavior is kept and pointed at LocalState. Haptics are handled in Aurora’s input init (rebase step 0005) |
| 4 | `host_context.cpp` fibers → `Ex` variants (2) | `ConvertThreadToFiber`/`CreateFiber` in `runtime/src/host_context.cpp`; guest threading correctness rides on this, so it gets its own tiny patch + a boot test |
| 5 | `guest_flat_memory.cpp` vectored handlers undeclared in App family | Same file/role in NSMBW. Hand declarations live in one guarded header used by both this and `memory.cpp`; no scattering |
| 6 | `memory.cpp` same declaration problem | Same treatment; DbgHelp-based crash naming in this file is log-only on Xbox |
| 7 | `host_cpu_baseline.cpp` startup CPU/environment checks (4) | NSMBW’s version also does a compat-build `CreateProcess` handoff and `MessageBoxA`. On the known console CPU: log the detected features and continue; no handoff process, no popup |
| 8 | `network_ssl.cpp` Schannel → stubs | NSMBW has both Schannel (Windows) and mbed TLS (non-Windows) paths. v1 is offline: guest TLS fails closed with a logged stub, neither path is ported. `cacert.pem` is therefore not packaged in v1 |
| 9 | `discord_presence.cpp` named pipe → out | Exclude the TU’s pipe transport under the define and force presence disabled; the config keys remain parseable so a PC `Config.toml` copied to the console does not crash startup |
| 10 | `cryptopp/zdeflate.cpp` `stdext` (2) | Same vendored Crypto++ in NSMBW (audit also flags `integer.cpp`). Replace with the standard-library equivalent under the Store compile, or exclude the affected TUs if the linker proves them unused — decide from the Phase 2 histogram, not in advance |

## NSMBW-only extras (no Mario Kart equivalent)

| Area | v1 treatment |
|---|---|
| `runtime/src/game_folder.cpp` — COM `IFileOpenDialog` + `MessageBoxW` first-run picker | No picker on Xbox. `EnsureConfigured()` under `NSMBW_UWP` accepts only the fixed contract: configured `dvd_root` (from our packaged `Config.toml`) pointing at `LocalState\GameAssets\DATA`; the existing `Problem()` validation (disc ID + revision from `sys/boot.bin`) stays fully in force and logs its verdict |
| `runtime/src/updater.cpp` — WinHTTP + `CreateProcess` self-update | Compiled out. Updates on Xbox = install a newer signed package; the in-game Update UI must not offer a dead button |
| `runtime/src/netplay/*` — LAN rooms, UDP sessions, process relaunch to start a session | Deferred wholesale. Session-start relaunch (`CreateProcessW`) cannot work in an AppContainer; a future netplay phase must redesign session start in-process. Couch co-op (multiple local controllers) is *not* netplay and stays in v1 |
| `runtime/src/hle/vi.cpp` — DWM timing query via `HWND` | Guard out with the other HWND code; presentation timing comes from SDL/Dawn |
| Settings overlay / input bindings — write `Config.toml`, `gamecontrollerdb.txt` beside user data | Keep, but every write must land under LocalState application data (follows automatically once change #1/#2 land — verify with a settings-change → relaunch test) |
| `runtime/src/host_suspend.cpp` | Audit before Phase 5 test 6. The recipe leaves Dev Mode suspension unsolved (returning from Home restarts the game); our v1 bar is “restarts cleanly, save survives” |

## Path contract (single source of truth)

```text
<PackageRoot>\                         (read-only, from the .msix)
  NSMBW.exe  *.dll  dsp_coef.bin  initial_pipeline_cache.db  wii_bootstrap\
<LocalState>\
  NSMBW\                               (SDL_GetPrefPath application folder)
    Config.toml                        (dvd_root = "../GameAssets/DATA")
    Logs\uwp-console.txt               (stdout/stderr, first thing written)
    Saves\  Cache\  NAND data\         (created by the runtime)
  GameAssets\DATA\                     (the owner's extracted game: files\ + sys\)
```

Relative `dvd_root` resolution follows the runtime’s existing “relative to the config folder” behavior — the same trick the recipe’s `Config.toml` uses. If `GameAssets\DATA` is missing or the wrong revision, startup must log *why* (the upstream `Problem()` strings) and exit cleanly; a black screen is a bug in our overlay, full stop.
