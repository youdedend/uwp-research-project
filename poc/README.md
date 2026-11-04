# POC — Smallest Proof of Concept (do this before any port)

**Purpose:** Prove, on *your* Series X|S in Dev Mode, the five risks that kill UWP ports — toolchain packaging, display/present, gamepad input, audio routing, writable storage — plus the 5 GB memory envelope, in a program small enough to debug in an evening. If this POC is painful, fix the stack choice now (see `docs/02-…` §E) while it's cheap.

No starter code is included yet on purpose: build it by adapting `uwp_gl_sample` (#21) or SDL3-UWP's `testdraw` (#23) so that every line exists because *you* needed it. Bring your build log back for review at Stage 3 of the learning plan.

## Spec

Baseline stack: **C++ · SDL3-UWP (pinned branch/release zip) · x64 WindowsStore · VS2022 UWP tools · CMake+Ninja or the `VisualC-WinRT` solution.** Renderer: `SDL_Renderer` (rung 1). Stretch goal only after acceptance: re-implement the same scene with raw D3D11 via `CreateSwapChainForCoreWindow`.

| # | Feature | Acceptance test |
|---|---|---|
| 1 | Install & launch | APPX installs via Device Portal on a fresh Dev Mode profile; Dev Home type set to **Game**; launches twice in a row; upgrade v1→v2 in place |
| 2 | Display | Clear color + one textured, slowly rotating quad, sized from *actual* display size (no hard-coded 1920×1080); survives TV resolution switch 1080p↔4K |
| 3 | Frame loop | On-screen FPS + frame-ms (P50/P95), timestep decoupled from present rate, clean quit to Dev Home |
| 4 | Gamepad | Left stick moves quad; A = color cycle; B = rumble pulse; Menu = pause overlay; unplug pad mid-move → paused "reconnect controller" screen, replug resumes; second pad detected and shown by ID |
| 5 | Audio | Looping tone/music + A-button blip via SDL audio; correct on TV speakers and controller headset; silence on suspend |
| 6 | Storage | On Y: write JSON (settings + launch counter) to LocalState (via SDL pref path); relaunch shows incremented counter; uninstall→reinstall resets it (proves you know where data lived) |
| 7 | Memory overlay | `MemoryManager` usage/limit + texture bytes you allocated, updated 2×/s; a debug key (X) allocates/releases a 256 MiB texture pool so you can *watch* pressure behaviour |
| 8 | Lifecycle | Guide → open another app → return: no crash, no leaked growth over 5 cycles; 30-minute idle soak |
| 9 | Logs | Timestamped log file in LocalState (init order, HRESULTs, pad events, memory samples) retrievable via Device Portal — your only console debugger for standalone runs |
| 10 | Golden image | Screenshot from console vs PC UWP build of same frame; differences (if any) explained in one paragraph |

## Build notes (learned from the case studies)

- Script your environment and **assert the Store CRT** (`%LIB%` contains `x64\store`) — Jadyx's `build-env.bat` pattern. Silent desktop fallback is failure mode #1.
- Minimum capabilities in `Package.appxmanifest`: start with *none* beyond defaults, add only when a test fails without one. Do not copy BurgerDoom's `runFullTrust`/`broadFileSystemAccess`.
- Stable Identity/Publisher + monotonic Version from the first package, so upgrade-in-place (test #1) is meaningful.
- Keep symbols for every package you install on the console (`poc_0.1.0_symbols.zip` habit, cf. Jadyx releases).
- Always validate PC-UWP *and* console standalone (no debugger — memory limits don't apply under the VS debugger).

## Definition of done

All 10 acceptance tests pass, performed once by you and once by following *only* a one-page README you write (install steps incl. type=Game). Timebox: 1–3 part-time weeks at beginner level. Exceeding it means: wrong rung on the renderer ladder, unpinned dependencies, or missing fundamentals (Stage 0–2) — return to `docs/03-…` §K.1 rather than starting a game port on a broken foundation.

## Then what?

Next experiments in order: D3D11 textured cube (DirectXTK sprites/text for UI) → Mesa OpenGL variant of the same quad (compare!) → only then open one real codebase at milestone M0 (`docs/02-…` §F).
