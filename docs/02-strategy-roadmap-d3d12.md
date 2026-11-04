# 02 — Strategy, Roadmap, D3D12 & Stack Guidance (E–H)

Target: **Series X|S · Dev Mode · UWP x64 · personal/testing**. Beginner pacing, expert detail. [Verified]/[Claimed]/[Inference] as before. Pseudocode is labeled and is **not** compile-ready.

---

## E. Recommended porting strategy and alternatives

### E.1 The recommendation (no game yet → learn in the right order)

**Primary path: C++ (or C) + SDL3-UWP + the simplest renderer that fits.**

1. Build `uwp_gl_sample`-class code (#21) → deploy to console.
2. Build a tiny *original* SDL game (you own it, no licensing fog) using SDL_Renderer (D3D11-class path) or OpenGL ES via SDL/Mesa.
3. Only then evaluate a real codebase with the matrix (`01-…` §D).

Why SDL first? Among reviewed sources it's the only dependency with versioned UWP branches, release zips, WinRT docs *and* GDK docs clearly separated (#23), zlib license, and it absorbs the four most painful UWP deltas for you: CoreWindow lifecycle, XInput gamepads, WASAPI audio, filesystem base/pref paths. Every other choice makes you hand-roll those before frame 1.

**Renderer decision ladder** (stop at the first rung that works — do not climb for prestige):

| Rung | Renderer | Choose when | Main cost |
|---|---|---|---|
| 1 | `SDL_Renderer` / software | 2D, retro, UI-heavy | Limited shaders/effects control |
| 2 | **Direct3D 11** (+ DirectXTK #7) via SDL window or own CoreWindow | Your code is D3D11, or modest 3D | Driver-managed (easy) but FL10.1/11.0 feature ceiling; still inside the 5 GB cap |
| 3 | OpenGL/GLES via **Mesa Gallium** (#25) or **ANGLE** (#28) | Your code is GL-native and small | Translation bugs, extension gaps, Meson-fork build chain |
| 4 | Vulkan via **Dozen** (#25; beware #11) | Your code is Vulkan-native, renderer rewrite is huge | Two translation layers (SPIR-V→DXIL inside); profiling is guesswork until measured |
| 5 | **Hand-written D3D12** (+ DirectXTK12/D3D12MA — upstream, not #19-fork) | CPU-bound draw submission, async compute/copy needs, or upstream already emits SPIR-V (the #8/#14 situation) | You become the memory manager, synchronizer, and shader-cache engineer. Months, not weekends. |
| 6 | WebGPU via Dawn-UWP (#24) | You *want* to bet on the future and can upstream fixes | Port completeness unproven — isolate behind abstraction |

### E.2 Alternatives honestly assessed

- **Commercial GDK route (#1–5):** Correct answer if "ship on the Store" ever replaces "run on my console." Bigger budgets (full GPU features, PIX on dev kits, Xbox services #29), but enrollment, NDA, certification, dev hardware. Learning UWP first still transfers: HLSL, controller UX, 10-foot design, memory budgeting.
- **The Forge (#6) on PC:** Superb for *learning* production D3D12/Vulkan abstraction without inventing your own. Its Xbox backend is not available to you in Dev Mode — treat it as a textbook with samples, or as your PC renderer whose *design* you re-implement thinly over D3D11/12-UWP. Don't plan a schedule around obtaining console access.
- **Streaming instead of porting:** A Moonlight-class UWP client (catalogued in #31) runs the PC binary remotely. Solves "binary-only game on TV" with zero porting legality issues; solves nothing about learning D3D12.
- **Do nothing on Xbox; learn D3D12 on PC only:** Legitimate if hardware access is the blocker. Microsoft's D3D12 samples + DirectXTK12 tutorials (linked from the UWP game guide) teach the same API; the UWP packaging/input chapter can be added later in weeks.

### E.3 What the libraries actually do (roles & limits)

| Library | Role | Verified limits from review |
|---|---|---|
| **SDL3-uwp #23** | Window/CoreWindow, input, audio, threads, IO; optional renderer | UWP sees only Xbox-compatible controllers; DLLs must be packaged; SDL_main needs C++ `/ZW` TU; cursor warping etc. unsupported (`README-winrt.md`) |
| **ANGLE #28** | GLES 2/3(.1) → D3D11 | D3D11 backend: ES3.1 "incomplete" upstream; this fork's UWP delta unverified. Not a D3D12 path |
| **Mesa-UWP #25** | Gallium GL-on-D3D12 · Dozen Vulkan-on-D3D12 · `spirv_to_dxil` | Needs Meson-UWP fork + `_XBOX_UWP`; three sub-projects mature at different rates; huge build (600 MB tree) |
| **mesa_ai_slop #11** | Experimental Dozen fixes (e.g. 16-bit lowering) | AI-authored per its own description, 0★, no releases. Diff every line; never float on `dozen-update` HEAD |
| **Dawn-UWP #24** | WebGPU API → D3D12 (+ Tint WGSL compiler) | "Early basic compatibility"; no releases. API is beginner-friendlier than D3D12 *if* it works |
| **The Forge #6** | Full rendering framework (PC/mobile public) | Console = commercial + accredited only. No physics/audio/network even on PC |
| **DirectXTK #7** | D3D11 helpers: SpriteBatch, models, XAudio2, GamePad | **D3D11 only.** For D3D12 use DirectXTK12 (different repo) |
| **D3D12MA #19→upstream** | Pooling/suballocation for D3D12 heaps | Solves *allocation*, not barriers/descriptors/PSOs. KytyPS5 uses it inside a much larger renderer |
| **libuwp #26** | Screen size/refresh, bundle paths, picker, event pump, pad callbacks | 3 tiny files; a shim, not an engine |
| **xbox-swap #27** | File-backed CPU allocation beyond commit cap | GPL-3.0; paging ≠ performance; last resort for guest-memory monsters |
| **switch-gdx #18** | LibGDX (JVM)→C++ transpile to UWP/Switch | GLES2-class, sockets broken, Clearwing runtime subset |

---

## F. Porting roadmap and milestones

Each milestone: **prereqs → likely changes → expected result → verify → common failure.** Assume the E.1 primary path unless noted. Timeboxes are beginner-with-mentor [Inference] — a codebase audit can move any row by 10×.

### M0 — Source & rights audit (½–2 days)
- *Prereqs:* repo access. *Changes:* none. Inventory per §D missing-info list; record licenses of game + every dep.
- *Result:* Go/no-go row in the matrix. *Verify:* game builds from clean clone on PC. *Failures:* "source available" but assets/build scripts missing; a binary-only plugin vetoes everything (find it now, not at M4).

### M1 — Toolchain (½–2 days)
- *Prereqs:* Windows 10/11 PC. *Changes:* Install Visual Studio 2022 with **C++ Universal Windows Platform tools** + Windows 10/11 SDK [pattern verified in Jadyx `uwp_build.md`]; CMake ≥3.25 + Ninja (preferred over VS generator — Jadyx documents silent desktop-fallback if `vswhere` isn't on PATH / Store CRT not selected).
- *Result:* `vcvarsall x64 uwp` shell; `%LIB%` contains `x64\store`. *Verify:* stock VS "DirectX 12 App (Universal Windows)" or SDL `testdraw` builds as x64 WindowsStore binary. *Failures:* silently building Win32 (deploys nowhere) — the classic; `/MT` deps colliding with `/MD` Store CRT (Jadyx OpenSSL saga).

### M2 — Minimal UWP app on console (1–3 days)
- *Prereqs:* Dev Mode console + Device Portal access (follow MS/community setup #22; verify against MS pages). *Changes:* Package.appxmanifest (Identity, x64, min capabilities), CoreApplication/SDL entry, assets/icons.
- *Result:* App installs via Device Portal/VS deploy, appears in Dev Home, **type set to Game** (unlocks the 5 GB/D3D12 game envelope vs 1 GB app envelope — every case-study README repeats this step). *Verify:* launches to a clear-color screen, suspends/resumes without crash. *Failures:* cert/publisher mismatch on reinstall; App-vs-Game type giving you 1 GB (mysterious OOM); dependencies (VCLibs) missing from package.

### M3 — Display + game loop (2–5 days)
- *Changes:* `CreateSwapChainForCoreWindow` (or SDL window) sized to actual display (libuwp `uwp_GetActualSize` pattern), resize/orientation, fixed/variable timestep, event pump (`SDL_PumpEvents` / `CoreDispatcher` / `uwp_ProcessEvents`).
- *Result:* 60 Hz clear + FPS counter on TV. *Verify:* test 1080p *and* 4K output modes; force resize. *Failures:* rendering before window exists; assuming desktop resolution; VSync/present interval misunderstandings causing 30 fps cap.

### M4 — Input (1–3 days)
- *Changes:* SDL_Gamepad or `Windows.Gaming.Input`; keyboard/mouse de-emphasized; menu navigation (d-pad/stick + A/B), disconnect handling (Jadyx rule: never silently swap a vanished pad), rumble later.
- *Result:* Full game playable pad-only, 10-foot UI focus visible. *Verify:* 2 pads, mid-game unplug/reconnect, Guide-button behavior observed (system reserves it). *Failures:* XInput-only assumptions about 3rd-party pads in UWP (#23 warning); text input without OSK plan.

### M5 — Rendering (1 week–6 months: the variance lives here)
- *Changes per ladder rung (E.1):* D3D11: device/context, HLSL SM5-era shaders, DirectXTK helpers. GL: link Mesa/ANGLE build, cap GL version/extensions, translate shaders offline where possible. Vulkan: package Dozen ICD, pin Mesa commit. D3D12: see §G — allocate months.
- *Result:* Your game's first real scene at reduced resolution (720p default is a *memory* feature, cf. gow3). *Verify:* PIX-on-Windows/`D3D` debug layer on PC first; on console compare screenshots vs PC golden images. *Failures:* shader compile at draw time (hitches — build a disk cache, M9), FL11.0-incompatible features (16-bit ops, barycentrics, mesh shaders — Kyty/Jadyx measured ceilings [Claimed]), desktop-GL extensions absent in translation layers.

### M6 — Audio (2–5 days)
- *Changes:* SDL audio (WASAPI backend) or XAudio2 2.9 (Jadyx/DirectXTK pattern); decode via permitted codecs; mic only with `microphone` capability + user consent (Kyty headset work shows the shape).
- *Verify:* TV vs headset routing, suspend/resume silence discipline. *Failures:* assuming desktop default-device semantics; sample-rate conversion stutter.

### M7 — Storage & assets (3–7 days)
- *Changes:* Install dir = read-only. Writable: `LocalState` (saves/caches). Large user content: removable storage / picked files (libuwp picker copies into aux root) — request only needed capabilities (`removableStorage` etc.; BurgerDoom's set is broader than most games need). Stream/chunk large assets; don't design around multi-GB single files without on-device tests.
- *Verify:* cold install → first-run extraction → save → reinstall-upgrade keeps saves (gow3/Jadyx upgrade-in-place promise). *Failures:* writing next to the exe; backslash/case-sensitivity from Linux-era code; USB removal mid-read.

### M8 — Networking (optional, 1–4 weeks)
- *Changes:* WinRT sockets/`wininet` partition limits; no raw desktop assumptions. Xbox Live features (achievements, cloud saves) are **not** available to a personal Dev Mode sideload — #29 tooling needs enrollment + sandboxes. Design LAN/direct-connect only if your game needs it (Melee successor claims Direct Connect tester reports [Claimed] — treat netcode as its own project).
- *Failures:* localhost assumptions, cert validation in AppContainer, background-socket expectations.

### M9 — Performance & memory (ongoing)
- *Changes:* 5 GB unified budget ledger (guest/app + GPU + shader caches); texture format discipline ( BC compression; Jadyx ASTC→BC3 transcode is the emulator version of "don't ship RGBA32"); shader precompile step vs on-demand hitch (expose the choice like gow3); resolution scaling; cache eviction near cap (Jadyx guard).
- *Verify:* 30-min soak (see §J). *Failures:* measuring PC working set instead of commit incl. GPU; discovering the cap under the VS debugger where limits don't apply [Verified trap].

### M10 — Packaging, deployment, testing (3–7 days, then forever)
- *Changes:* Versioned APPX/MSIX + dependency packages; symbols kept (Jadyx ships `*_symbols.zip` — copy that practice); SHA256SUMS; install/upgrade/uninstall matrix on Series S *and* X if you can.
- *Verify:* fresh-console install by a second person following only your README. *Failures:* publisher/cert churn breaking upgrades; forgetting Dev Home type=Game in instructions.

### Smallest useful proof of concept
See [`../poc/README.md`](../poc/README.md): clear screen → spinning textured quad/cube → pad moves it → WAV plays on button → saves a file → FPS + `MemoryManager` overlay → survives suspend/resume. If this takes >2–3 weeks part-time, your stack/toolchain choice is wrong — fix that before touching a real game.

---

## G. D3D12 concepts relevant to this project

### G.0 First: do you need D3D12 at all?

Microsoft's own guidance (game-tech guide): use D3D12 when CPU-bound and prepared to manage resources yourself for expert-level control; D3D11 trades peak efficiency for a driver-managed model. On UWP-Series both are FL11.0 hardware — D3D12 does **not** unlock extra GPU features there, it unlocks *lower CPU overhead and explicit memory/sync* (and explicit ways to crash). For a beginner SDL game, D3D12's relevant value is *educational*. Learn the concepts below on PC with samples; ship the game on rung 1–3 until profiling says otherwise. **Do not start a port with a D3D12 rewrite** — the two repos that did (KytyPS5, Jadyx) had SPIR-V pipelines and full-time authors.

Progression (each concept: what it is → why it matters here → what breaks):

1. **Device & feature levels.** `D3D12CreateDevice` at FL11.0 for UWP-Series safety; query optional features, never assume desktop. *Breaks:* requesting FL12+ features/mesh shaders → device-creation or PSO failure on console while PC passes.
2. **Command queues, allocators, lists.** You record lists, reset allocators only after GPU completion (fences), submit to DIRECT/COMPUTE/COPY queues. *Here:* emulator backends record guest draws 1:1 — list/allocator lifetime dominates their CPU cost. *Breaks:* resetting early = GPU reading garbage, nondeterministic corruption.
3. **Swap chain for CoreWindow.** DXGI flip-model, `CreateSwapChainForCoreWindow`, present with fences per backbuffer. *Here:* identical idea on SDL's D3D paths; resize = drain GPU first. *Breaks:* resizing with frames in flight → `DXGI_ERROR_DEVICE_REMOVED`-style failures.
4. **Resources & heaps.** Buffers/textures are placed/committed in heaps (DEFAULT/UPLOAD/READBACK); D3D12MA (upstream of #19) suballocates so you don't write a heap allocator on day one. *Here:* everything counts against the shared 5 GB — heap budgets are gameplay budgets. *Breaks:* one committed heap per texture = fragmentation OOM at 60% "used."
5. **Descriptors & descriptor heaps.** CBV/SRV/UAV/RTV/DSV/sampler tables replace D3D11's bind slots; shader-visible heaps have strict size limits. *Here:* Kyty hit the 2048-sampler heap overflow until writing samplers once per list. *Breaks:* CPU-writing descriptors the GPU still reads (needs versioning/ring allocation).
6. **Root signatures & root constants.** The contract between CPU bindings and shaders; small data (e.g. Kyty's clip planes) rides as root constants. *Breaks:* mismatch = validation errors/black draws; over-large signatures cost per-draw.
7. **Pipeline State Objects (PSOs).** Shaders + all fixed state baked into one object; creation is expensive → caches (in-memory, disk, "precompile" UX). Shaders are DXIL (HLSL → DXC; SPIR-V→DXIL via Mesa for translated workloads; `dxil.dll` signs on-device in emulator flows). *Breaks:* creating PSOs mid-frame = the infamous shader-compilation stutter (gow3's 3-minute/7k-shader preload is this, productized).
8. **Resource barriers & states.** You declare transitions (RENDER_TARGET → SHADER_RESOURCE etc.); split barriers, UAV barriers, aliasing barriers. *Breaks:* missing barrier = corruption that may only appear on the console's tile-based timing; excessive barriers = pipeline stalls.
9. **Synchronization: fences & frame pipelining.** CPU↔GPU and queue↔queue sync is yours; standard pattern = fence value per frame slot, wait only when reusing that slot. *Breaks:* waiting every submit (GPU idle, "D3D12 slower than D3D11!") or never waiting (use-after-free).
10. **Memory residency & budgeting.** `QueryVideoMemoryInfo`-style discipline + UWP `MemoryManager` pressure events; evict/shrink caches before the OS terminates you (Jadyx ledger/guard). On unified memory there's no separate VRam to hide in.
11. **What you can defer:** mesh/amplification shaders, sampler feedback, VRS tiers, DXR raytracing, work graphs, Agility SDK features (unavailable per Jadyx [Claimed]), multi-GPU, predication exotica. None gates a Dev Mode learning project.

**Mental mapping for translators:** Vulkan→D3D12 (Dozen) ≈ same explicit model (that's why translation is feasible); GL→D3D11/12 (Mesa/ANGLE) = implicit→explicit (the layer invents barriers/caches — where its bugs live); D3D11→D3D12 (11on12 / rewrite) = re-owning everything the driver did.

---

## H. Language- and engine-specific guidance

Assumptions for all snippets: Windows PC, VS2022 UWP tools, x64 WindowsStore target, console in Dev Mode. **Pseudocode is labeled; library calls must be checked against the pinned version's headers.**

### H.1 C++ + SDL3-UWP (recommended starter)

Where things live: SDL from #23 (`VisualC-WinRT` solution or CMake WindowsStore build), your game as x64 UWP exe + `Package.appxmanifest`, assets in package or LocalState.

```cpp
// PSEUDOCODE — shape only. One .cpp compiled with /ZW includes SDL_main
// (per SDL README-winrt.md); real error handling omitted.
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
int main(int, char**) {
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD | SDL_INIT_AUDIO);
    SDL_Window* win = SDL_CreateWindow("poc", 1280, 720, 0);
    SDL_Renderer* ren = SDL_CreateRenderer(win, nullptr); // D3D-backed on UWP
    bool running = true;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {           // also pumps UWP lifecycle via SDL
            if (e.type == SDL_EVENT_QUIT) running = false;
            // handle SDL_EVENT_GAMEPAD_* here
        }
        SDL_RenderClear(ren); /* draw quad */ SDL_RenderPresent(ren);
    }
}
```
Key UWP deltas vs desktop SDL: base/pref paths come from SDL's filesystem APIs (don't `fopen("save.dat")` against CWD); packaged DLLs only; minimize desktop-only SDL hints; test gamepad-first.

### H.2 C++ + D3D11 (next step up)

Use SDL only for window/input (get `CoreWindow` via SDL window properties per `README-winrt.md`, then `IDXGIFactory2::CreateSwapChainForCoreWindow`), or go pure CoreApplication + DirectXTK (#7: `GamePad`, `SpriteBatch`, XAudio2 `Audio.h`). Shaders HLSL compiled offline (FXC/DXC SM5.x targets) and loaded from package files. This is the highest rung where Microsoft still owns memory/sync — ideal first 3D.

### H.3 C++ + OpenGL legacy code

Mesa path (#25): build with the Meson-UWP fork (`--backend=vs --uwp`, `_XBOX_UWP` defines [Verified: repo README]), link like #21 (glad loader + Gallium). Cap to a *profiled* GL subset; log every extension you touch; keep a D3D11 fallback for problem shaders. ANGLE path: treat as GLES2/3.0→D3D11; verify ES3.1 features individually.

### H.4 C++ + Vulkan legacy code

Package a pinned Dozen build (from #25 lineage; if using #11 fixes, vendor + review them as patches). Validate with Vulkan validation layers on PC first (Dozen won't give WindowsStore-friendly layering miracles). Profile draw/dispatch translation hotspots early — if descriptor/PSO churn dominates, the honest fix is §G rung 5 (budget accordingly).

### H.5 C# / Unity

Two different animals: (a) **Unity UWP export** (legacy, version-pinned; IL2CPP; plugins must be WinRT-partition-safe; `.NET` backend history matters) — community guides in #30, verify against your Unity LTS release notes; memory: the 5 GB cap includes IL2CPP + assets, and "runs on PC UWP" ≠ "fits Series S." (b) **Unity GDK** (#4) — commercial only. Rule: if a tutorial says "Build Settings → Xbox" without mentioning UWP vs GDK explicitly, stop and identify which world it's in.

### H.6 Java/Kotlin + LibGDX

switch-gdx (#18): JVM bytecode → C++ via Clearwing; JDK17 + CMake/Ninja toolchain on the PC side. Constraints from README: GLES2-class rendering, Box2D/Bullet/FreeType/Controllers supported, sockets/GL30 not. Suitable for existing small LibGDX titles; unsuitable as a way to learn D3D12.

### H.7 Godot / Defold / Unreal / Rust

- **Godot:** 3.x UWP export (docs linked from #30) is the only Dev Mode story in reviewed sources, with known community bug-fix repos; Godot 4 → GDK commercial mentions only. Pinning an old engine major version for a hobby sideload can be rational — decide with eyes open.
- **Defold/Unreal:** commercial GDK only per #5 / absence of any UWP evidence. Don't schedule Dev Mode milestones around them.
- **Rust:** No reviewed official UWP-Xbox toolchain. A Rust-core + C++ UWP shell (SDL/D3D11 in C++, Rust staticlib via FFI, WindowsStore-partition audit of every crate) is conceivable R&D — I mark it ❔, not a plan. Revisit only after M1–M3 in C++ feel boring.

### H.8 If your real stack turns out unsupported

Nearest documented alternatives, in order of code preservation: (1) keep game logic, replace platform layer with SDL shim (most C/C++ ports); (2) keep renderer API, insert translation layer (GL/Vulkan rows above); (3) keep assets/design, reimplement in SDL/C++ (binary-only or dead-engine cases); (4) switch goal to GDK commercial or PC-only D3D12 learning. Sunk-cost discipline: M0 exists to force this conversation while it's still cheap.
