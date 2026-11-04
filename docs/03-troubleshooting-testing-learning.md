# 03 — Troubleshooting, Testing, Exercises & Checklists (I–L)

Target reminder: **Series X|S · Dev Mode · UWP x64 · personal use.** Fixes labeled [Documented] come from reviewed MS/repo docs; [Workaround] = community practice — retest after OS/toolchain updates.

---

## I. Troubleshooting handbook

Format per issue: **Symptoms → Probable causes → Diagnose → Fix → Prevent.**

### I.1 Build silently produces Win32, not UWP
- **Symptoms:** Builds fine, deploys nowhere; or desktop APIs link happily then fail on device.
- **Causes:** `vcvarsall` fell back to desktop env (Jadyx documents `vswhere.exe` off PATH → silent fallback); CMake `CMAKE_SYSTEM_NAME` not `WindowsStore`; WINAPI partition still `DESKTOP_APP`.
- **Diagnose:** `echo %LIB%` must contain `x64\store`; check `VSCMD_ARG_app_plat=UWP`; run Jadyx-style `build-env.bat` verification; `dumpbin /headers` + inspect subsystem/imports.
- **Fix [Documented in #14]:** put VS Installer dir on PATH, `vcvarsall x64 uwp`, CMake preset with WindowsStore + Ninja.
- **Prevent:** check-in a build-env script that *asserts* Store CRT; CI the UWP target from day 1.

### I.2 CRT/link errors: LIBCMT vs MSVCRT, `/MT` vs `/MD`
- **Symptoms:** LNK2038 runtime mismatch; unresolved `__imp_*` desktop symbols.
- **Causes:** prebuilt `/MT` dependency (Jadyx had to source-build OpenSSL); mixing desktop `.lib`s.
- **Diagnose:** `/verbose:lib` link log; inventory every dep's runtime flag.
- **Fix:** rebuild deps from source under Store CRT (`CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL`-style policy); never mix.
- **Prevent:** dependency depot built once per toolchain (WWHD/Melee overlays formalize this).

### I.3 App runs under debugger, OOMs standalone
- **Symptoms:** `8007000E` / texture creation fails only when launched from Dev Home.
- **Causes:** Memory limits **don't apply under VS debugger** [Verified: MS resource page]; or app type = App (1 GB) not Game (5 GB).
- **Diagnose:** overlay `Windows.System.MemoryManager` `AppMemoryUsage/AppMemoryUsageLimit`; check Dev Home app type; measure *commit incl. GPU*, not PC working set.
- **Fix:** set type=Game; budget to 5 GB unified (see J.2); shrink texture formats/resolution; add cache eviction.
- **Prevent:** weekly standalone (no-debugger) soak; fail CI if PC commit exceeds budget minus safety margin.

### I.4 Black screen, app alive (audio/input work)
- **Causes:** swapchain created before CoreWindow ready; wrong window handle path (SDL properties vs HWND thinking); zero-size backbuffer after resize; event pump starved (`uwp_ProcessEvents` never called without SDL).
- **Diagnose:** log activation → window size → first `Present` HRESULT sequence to LocalState file; test with clear-color-only frame.
- **Fix:** create/resize swapchain only on valid size; follow SDL `README-winrt.md` CoreWindow flow or DirectXTK `DeviceResources` pattern.
- **Prevent:** golden-path smoke scene (POC) kept runnable behind a flag forever.

### I.5 Shader fails on console, fine on PC
- **Symptoms:** PSO creation fails; draws dropped; guest draws "skipped" in emulator logs.
- **Causes:** FL11.0 ceiling (no mesh shaders/barycentrics/native 16-bit assumptions — Kyty/Jadyx apply explicit `xbox_gpu_limits`-style caps [Claimed measurements]); SM target too high; DXIL signing/`dxil.dll` mismatch in translated stacks; GL extension absent in Mesa/ANGLE.
- **Diagnose:** enable D3D12 debug layer + GPU-based validation **on PC** at FL11.0; log compile HRESULTs + shader hash; bisect with a passthrough shader.
- **Fix:** clamp feature requests, add 32-bit fallbacks (cf. #11 lowerings — review, don't blindly adopt), precompile at build/load time into a versioned disk cache.
- **Prevent:** shader "caps header" shared PC/console; screenshot-compare suite per shader family.

### I.6 First-minute stutter, then smooth (shader compilation)
- **Causes:** PSO creation on first draw (gow3: 7k shaders ≈ 3 min preload vs pop-in choice).
- **Diagnose:** frame-time log split by compile/submit/present (gow3 `SPARTAN_FRAME_STATS` pattern).
- **Fix [pattern in #8/#9/#14]:** persistent pipeline/shader disk cache keyed by hash+toolchain version; optional precompile step; background warm-up during loading screens; cap concurrent compiles.
- **Prevent:** cache invalidation policy from day 1 (app version + driver/OS build in key).

### I.7 Controller: no input / wrong pad / drops mid-game
- **Causes:** polling XInput indices desktop-style; UWP only exposes Xbox-compatible controllers via SDL path [Documented #23]; focus lost (system overlay); "helpful" auto-reassign on disconnect (Jadyx explicitly forbids silent replacement).
- **Diagnose:** log `GamepadAdded/Removed` (SDL events or `Windows.Gaming.Input`); show pad ID+model on debug overlay (Kyty lists by model).
- **Fix:** event-driven pad management; pause-on-disconnect UX; rebind screen; test 1–4 pads.
- **Prevent:** pad-only playtest every milestone; never gate progress on keyboard/mouse.

### I.8 Files: works on PC UWP, `ACCESS_DENIED` / not found on console
- **Causes:** writing to install dir; assuming CWD; USB paths without capability/*FromApp APIs; case-sensitivity; drive letters differing (case studies use `D:\DevelopmentFiles`, USB roots, LocalState).
- **Diagnose:** log resolved absolute paths + `GetLastError` to LocalState; reproduce with USB removed.
- **Fix:** SDL base/pref paths or `ApplicationData.LocalFolder`; request minimum capabilities (`removableStorage` when needed — avoid copying BurgerDoom's `runFullTrust`+`broadFileSystemAccess` unless you can justify each); use picker + copy-in (libuwp pattern) for user content.
- **Prevent:** storage abstraction with three roots only: Package (RO), LocalState (RW), UserPicked (transient).

### I.9 Package installs but won't upgrade / duplicate apps
- **Causes:** Publisher/Identity/version churn; cert changed between builds.
- **Diagnose:** compare AppxManifest Identity across builds; Device Portal error codes on install.
- **Fix [Workaround, gow3/Jadyx practice]:** single stable test signing identity for the project (understand: self-signed = vouches for nobody, Dev Mode testing only); monotonic versions; ship dependency appx (VCLibs) + symbols + SHA256SUMS like Jadyx releases.
- **Prevent:** release checklist + fresh-profile install test (§J).

### I.10 Device Portal / deployment connection failures
- **Causes:** console not in Dev Mode (retail/developer partitions are separate worlds — dev packages don't run in Retail and vice versa); network isolation; PIN/pairing expired; HTTPS cert warnings on the portal.
- **Diagnose:** ping console, open Device Portal in browser first (Kyty/gow3 dev logs validate via portal before VS deploy), try VS "Remote Machine" rediscovery.
- **Fix:** follow MS Dev Mode activation docs + #22 setup guides step-for-step; same subnet; reboot-to-Dev-Mode confirmed in Dev Home.
- **Prevent:** wired Ethernet for both; document console IP reservation.

### I.11 GPU hang / device removed on console only
- **Causes:** barrier/state errors, descriptor use-after-free, sampler-heap overflow (Kyty's 2048 case), unbounded dispatch (Jadyx workgroup-split case study: correct results, 80 ms atomics-bound dispatch).
- **Diagnose:** PC repro at FL11.0 with debug layer; per-pass GPU timestamps; bisect passes; check `GetDeviceRemovedReason` and log it before exit (Jadyx returns to library on GPU failure — copy that resilience).
- **Fix:** fix validation errors in order; version descriptors per frame-slot; cap heap writes per list.
- **Prevent:** never ship with validation errors "that seem harmless on PC."

### I.12 Mesa/Dozen/ANGLE layer bugs (wrong colors, missing effects)
- **Causes:** translation gaps (format/tiling — Kyty R8/R16 detiling notes; ANGLE ES3.1-on-D3D11 incompleteness), floating on `main` HEAD.
- **Diagnose:** same scene on PC native API vs translated; single-quad repro; layer version bisection.
- **Fix:** pin layer commit + carry reviewed patches; feature-flag offending effect; D3D11 fallback path for that pass.
- **Prevent:** visual regression screenshots in CI-on-PC with the *pinned* layer build.

---

## J. Testing and optimization plan

### J.1 Correctness testing (do in this order)
1. **PC UWP build** (WindowsStore target locally) — catches partition/CRT/path bugs without a console round-trip. Every serious case study validates PC+Series pairs.
2. **Console smoke matrix:** cold launch · suspend (Guide → other app) → resume · pad disconnect · USB yank (if applicable) · resolution switch 1080p↔4K · 30-min soak · upgrade-in-place · uninstall/reinstall.
3. **Golden images:** scripted camera path, screenshot compare PC vs console (tolerance for translation layers).
4. **Content tests:** largest level, worst shader-compile area, save/load loop ×20, settings extremes (max resolution/textures) — the exact spots gow3/Jadyx document failing first.

### J.2 Performance & memory testing
- **Budgets [Verified caps]:** 5 GB unified (Game type), FL11.0. Set internal targets below caps (e.g. warn 75% / shrink 85% / shed 93% — Jadyx-style tiers [Inference: pick your numbers by testing]).
- **Measure:** frame-time percentiles (not avg FPS), CPU submit time vs GPU pass timestamps, shader-compile time separated from steady state, `MemoryManager` usage + limit overlay, texture/heap sub-allocations.
- **Tools:** on PC — PIX for D3D12 (MS game guide), Visual Studio diagnostics, D3D debug layer. On console UWP you largely get **your own overlay + logs via Device Portal** (Kyty/gow3 stats overlays are the pattern) — full PIX-on-xbox profiling belongs to the GDK/dev-kit world; don't plan around it. I state this plainly because tutorials blur it.
- **Frame pacing:** flip-model present intervals, ring of frame slots with fences (§G.9); test on 60 Hz *and* 120 Hz displays if available; input-latency test = pad→photon manual check with slow-motion phone video (cheap, effective).
- **Series S vs X:** same caps, very different GPU/bandwidth. If you only own one, default internal resolution conservatively (gow3 ships 720p default for memory; Jadyx reports per-model tables) and expose a resolution option.
- **Suspend/resume & lifecycle:** games terminate in background [Verified] — autosave on suspending event, restore deterministically, test mid-load suspend.

### J.3 Optimization order of operations
1. Fit memory (formats, mips, streaming, cache caps) → 2. Kill hitches (shader cache, async loads) → 3. CPU submit (batch draws, fewer state changes; only here does D3D12 start paying rent) → 4. GPU passes (resolution scale, occupancy — Jadyx GPU doc: feed hundreds of waves, watch VGPR/atomics latency, measure per-dispatch on console) → 5. I/O (USB vs internal, compression). Never optimize 4 before 1 on this platform.

---

## K. Learning plan, exercises, review questions (+ answer key)

### K.1 Staged learning roadmap (beginner → porting-ready)
| Stage | Do | Sources | Exit criteria |
|---|---|---|---|
| 0 Foundations | C++ refresh (RAII, COM `ComPtr` basics), Git, CMake presets | VS docs | Build any CMake+ Ninja hello-world |
| 1 SDL on PC | Original 2D micro-game, gamepad + audio + save file | #23 docs/examples | Pad-only play, clean quit |
| 2 UWP on PC | Same game as WindowsStore x64; manifest, LocalState saves | #23 `README-winrt`, #26 | Installs as UWP locally |
| 3 Console | Deploy POC (`poc/README.md`) to Series in Dev Mode | #21, #22, §F M2–M4 | POC checklist green |
| 4 Read a small port | BurgerDoom UWP diff end-to-end; write 1-page delta summary | #15 | Explain every manifest capability it requests |
| 5 D3D11 | Textured cube + DirectXTK sprites/text on console | #7 wiki, MS D3D11 UWP tutorial | Screenshot-matches PC |
| 6 Translation layers | GL sample via Mesa (#21/#25); log extensions; break/fix one shader | #25 README | Written note: 3 gaps found |
| 7 D3D12 concepts | MS D3D12 samples on PC (triangle→textured→compute); then UWP D3D12 template | §G, DirectXTK12 (find it!), #6 unit tests as reading | Explain fences/barriers/descriptors unprompted |
| 8 Read a big port | Kyty `XBOX_CHANGES.md` OR Jadyx `docs/xbox/uwp_build.md`+`xbox_series_gpu.md`; map each trick to the cap that forced it | #8/#14 | Oral/written quiz (K.2) ≥80% |
| 9 Real assessment | Run §D matrix + §L intake on a codebase you own | `01-…` §D | Written go/no-go with estimates |

### K.2 Exercises (do, don't just read)
1. **Env trap:** Deliberately build desktop vs UWP; capture `%LIB%` evidence of each; write the assert script.
2. **Memory wall:** In POC, allocate textures until `MemoryManager` reports pressure; graph usage vs resolution (720p/1080p/4K targets).
3. **Capability audit:** Diff BurgerDoom's manifest vs your POC's; justify/remove each extra capability.
4. **Shader hitch:** Force runtime shader compilation mid-frame; measure; move to load-time cache; measure again.
5. **Pad chaos test:** Script disconnect/reconnect ×10 during play; fix every crash/hang found.
6. **Layer A/B:** Same GL scene via Mesa vs native D3D11 rewrite of one pass; screenshot-diff and time both.
7. **License drill:** For SDL+Mesa+your game, produce a `THIRD_PARTY.md` with exact license texts (gow3 `xbox/CREDITS.md` is the model).
8. **Upgrade drill:** Ship POC v1, save data, install v2 over it via Device Portal; prove saves survive; document cert/identity stability.
9. **Series min-spec:** If only Series X available, emulate S discipline: cap internal res + texture pool, re-soak 30 min.
10. **Post-mortem:** Pick one archived/stalled repo (#12 or #17-successor); write why it stalled and what you'd do differently at M0.

### K.3 Review questions
1. Why does "Unity supports Xbox" not imply a Dev Mode build? Which two routes exist?
2. Your UWP game gets how much memory as App vs Game, and why didn't the debugger warn you?
3. DirectXTK (#7) targets which API? What is the D3D12 equivalent called?
4. Name Mesa-UWP's three distinct deliverables and one consumer of each in the set.
5. Why did KytyPS5/Jadyx write D3D12 backends instead of using Dozen like gow3? When is Dozen the smarter first move?
6. What does xbox-swap actually trade, and why shouldn't a normal game need it?
7. List four UWP platform deltas SDL absorbs for you.
8. A friend sends you a compiled PC game + "port this." What three things do you ask for before estimating?
9. Why is `runFullTrust` in a sample manifest a smell for your own game?
10. Your console build is black-screen but PC UWP works. Give a 5-step diagnostic order.

### K.4 Answer key (condensed)
1. Unity Xbox page = GDK/registered-dev route; Dev Mode = legacy UWP export, version-sensitive. Different SDK/packaging/cert. (§A.2/H.5)
2. 1 GB App / 5 GB Game foreground [MS]; limits waived under VS debugger → standalone OOM surprise. (§I.3)
3. D3D11. Equivalent: DirectXTK12 (separate repo, linked from MS guide). (§B.1)
4. Gallium GL-on-D3D12 (#21), Dozen Vulkan-on-D3D12 (#9/#13), `spirv_to_dxil` (#8/#14 shader translation). (§B.4)
5. Upstreams already emitted SPIR-V and needed control/perf/features beyond Dozen's maturity; Dozen first when renderer rewrite cost dwarfs translation tax and profiling hasn't condemned it. (§C.1/E.1)
6. Disk latency/stall risk for commit headroom; paging cold CPU memory, not creating RAM. Budgeting/content discipline is the real fix. (§B.4/J.3)
7. CoreWindow lifecycle+swapchain surface, gamepad (XInput constraints), WASAPI audio, filesystem paths/packaged-DLL rules. (#23)
8. Source + license/permissions; exact buildable toolchain/deps on PC today; renderer/middleware/memory profile. (§A.4/D)
9. It widens sandbox assumptions and copy-paste risk; request minimum capabilities you can justify per feature. (§I.8)
10. Check logs (activation→size→Present HRESULTs) → clear-only frame → event pump → swapchain resize discipline → PC FL11.0 validation. (§I.4)

---

## L. Final readiness checklist and further reading

### L.1 Intake (bring me these for a real verdict)
- [ ] Repo + LICENSE, confirmation of modification/deployment rights, asset provenance
- [ ] Clean-clone PC build log (compiler/SDK/engine exact versions)
- [ ] Dependency inventory (name, version, license, binary vs source, Win32-only?)
- [ ] Renderer: API, shader language/count, features used (compute? tessellation? 16-bit?)
- [ ] Peak PC commit memory incl. GPU; largest files; streaming design
- [ ] Input/audio/network/save systems; middleware (physics, video, voice)
- [ ] Target min-spec decision: Series S included? Internal-resolution budget?

### L.2 Pre-port readiness
- [ ] M1 toolchain script asserts Store CRT; UWP CI build green
- [ ] POC (`poc/README.md`) green on your actual console
- [ ] Renderer rung chosen with written reasoning (E.1) + fallback rung identified
- [ ] 5 GB budget ledger spreadsheet (app/GPU/caches/OS headroom)
- [ ] Storage roots (Package/LocalState/Picked) + capability list justified line-by-line
- [ ] Shader-cache + upgrade-in-place + symbols/release process drafted
- [ ] THIRD_PARTY licenses collected; GPL/MPL obligations understood for your distribution (even sideload sharing counts — get advice if unsure)

### L.3 Ship-to-yourself (Dev Mode "done")
- [ ] Fresh-install by second person from README only; type=Game step included
- [ ] 30-min soak Series S-min settings; suspend/resume ×5; pad chaos ×10 — no crash/leak growth
- [ ] Frame-time P95 within budget at default settings; first-run shader experience acceptable (precompile or tolerable hitches)
- [ ] Saves survive upgrade; uninstall clean; version + SHA256SUMS published with package
- [ ] README states: experimental/personal use, no game assets included (if applicable), known issues honest (gow3 README is the tone model)

### L.4 Further reading (in dependency order)
1. MS: Windows game development guide (UWP) + *System resources for UWP apps and games on Xbox* (previous-versions) — your caps/F11.0 source of truth.
2. MS: D3D12 programming guide + DirectX-Graphics-Samples; PIX on Windows docs.
3. DirectXTK wiki (#7) → then DirectXTK12 repo/wiki (discover its UWP/Xbox notes yourself — exercise).
4. SDL `README-winrt.md` vs `README-gdk.md` side-by-side (#23) — the two-worlds lesson in one sitting.
5. `uwp_gl_sample` (#21) code → BurgerDoom (#15) manifest/CMake → libuwp (#26) headers.
6. KytyPS5 `XBOX_CHANGES.md` (#8) and Jadyx `docs/xbox/` (#14) — graduate-level cap-driven engineering.
7. GDK world when ready: devdocs.xbox.com onboarding + porting path (#2), ID@Xbox (#1), Unity GDK docs (#4).

*Re-verify everything time-sensitive (Unity/Godot UWP status, repo activity, MS page moves) at the moment you start each stage. This ecosystem — one 404 (#17) and one archived repo (#12) in a single link list — does not sit still.*
