# 05 — PS3 / PS4 / Switch Ports Deep Dive for Xbox Series S (Dev Mode)

**Your hardware:** Xbox **Series S** in Developer Mode. **Families in scope:** the 49 game pages from `docs/04` — PS3 (16 games / 18 ports), PS4 (20 / 39), Nintendo Switch (13 / 18) — from ports.matheusbrauna.com.br (snapshot 2026-11-04), plus the Xbox-side projects that change the answer: `emelin2004/rpcs3-xbox`, `coopmatth/CellBox`, `AmitAmit99/shadPS4-xbox`, `Shiney-X/xbox-series-d3d12`, and `JulianDr14/jadyx`.

**Conventions:** [Verified] = read in code/README/releases via GitHub API on 2026-11-04 · [Claimed] = project/community report, not built or run by me · [Inference] = my engineering judgment. I did not compile any of these projects or run them on a console. No instructions for obtaining/decrypting game dumps, firmware, keys or BIOS files are included — every route assumes your own legally obtained copy. Re-check branches/licenses before copying code.

---

## 0. Verdict in 60 seconds

> **On a Series S, these three families invert the usual advice.** For *playing* games, the winning routes are the emulators that already exist on Xbox (RPCS3-xbox for light PS3, Jadyx for many Switch titles). For *porting the catalog's PC recomp/native-execution projects*, PS4 2D titles are the only D4-class research candidates; PS3 recomp and Switch recomp remain D5 research programs, not game ports. Series S does not lower the documented 5 GB UWP "Game" memory cap — it lowers GPU throughput, memory bandwidth headroom, and your safety margin underneath that same cap.

| Family | Play something this month (Series S) | Port a catalog PC project (Series S) | Best first research target |
|---|---|---|---|
| **PS3** | ✅ Light titles via `rpcs3-xbox` [Claimed: rel. v0.1.35.14, XMB 60 fps warm, several playable games] — catalog heavyweights unproven | ❌ D5 (one D4 pair). No ps3recomp UWP precedent found | Learn from CellBox's D3D12 RSX backend; if porting, Soulcalibur II HD *after* a runtime exists |
| **PS4** | ⚠️ `gow3_xbox` alpha (God of War III R.) is the only catalog-adjacent playable pattern; general shadPS4-on-Xbox does **not** run games yet [Verified in both projects' own docs] | ⚠️ D4 for 2D/arena, D5 for AAA/open-world | Odin Sphere / Dragon's Crown (2D), then WipEout Omega (gow3-framework sibling) |
| **Switch** | ✅ Many titles via Jadyx [Claimed Series S reports: Pokémon Legends: Arceus 30 fps, Yo-kai Watch 4++ 27–30 fps]; TotK hits memory wall even on Series X [Verified: Jadyx compat doc] | ❌ D5 / BX. No Switch-recomp UWP precedent found | None for a first port. Study Jadyx's D3D12 renderer instead |

**What changed since doc 04:** the discovery that RPCS3 already runs — with releases and a game-compat table — on Series X|S. That does **not** make catalog PS3 *recompilations* easier (still D5); it makes most PS3 recomp-to-Xbox work strategically pointless unless your goal is learning Cell/RSX translation or beating the emulator on a specific title.

---

## 1. Series S budget sheet (the numbers every gate uses)

Official UWP-on-Xbox allocation (Microsoft Learn previous-versions page, verified in doc 01): foreground memory **App 1 GB / Game 5 GB**, background 128 MB; CPU **Game = 4 exclusive + 2 shared cores**; GPU **full available cycles** for Games; **Series X|S UWP = DirectX 11 + DirectX 12, Hardware Feature Level 11.0**; **x64 only**. Limits are not enforced under the Visual Studio debugger — always verify standalone.

| Budget item | Series S reality | Why it bites these families |
|---|---|---|
| Unified app memory | 5120 MiB for CPU **and** GPU resources together | Double-copy problem: guest RAM + GPU-format textures + shader/PSO caches + JIT/recomp code all share one pool (Jadyx's TotK ledger: emulated Switch memory alone ≈2460 MiB) |
| CPU for translation layers | 4 exclusive + 2 shared Zen 2 cores | RPCS3-class PPU/SPU LLVM and Switch AArch64 JIT want more threads; thread oversubscription = stutter, not just lower fps |
| GPU features (UWP view) | FL 11.0 / SM 6.4 class, wave64, no barycentrics/mesh shaders/native 16-bit ops/heap indexing [Verified: shadPS4-xbox XBOX_PORT.md, from KytyPS5 notes; Jadyx README] | Modern Vulkan 1.3 renderers and SM 6.6-style bindless designs must be lowered/rewritten |
| Graphics APIs | D3D11/D3D12 only. **No platform-provided native Vulkan or OpenGL driver** in AppContainer (app-bundled Mesa/ANGLE-style layers are how you get them) | Every "Vulkan" row means Mesa Dozen-on-D3D12 *or* a D3D12 backend rewrite; every "OpenGL" row means Mesa Gallium or a new presenter |
| Shader signing | Runtime DXIL must be signed (`dxil.dll`); CellBox argues unsigned/runtime DXIL is rejected for PSOs and pre-bakes signed DXIL offline [Claimed in its README] | Shader-cache design is a first-order architecture decision, not an optimization |
| PSO caching | `GetCachedBlob()` / `CreatePipelineLibrary()` reported to *remove the device* in Dev Mode [Verified: jajdp/rush2-xbox, doc 04] | Keep DXIL, build PSOs at draw/boot (Jadyx model), release idle PSOs |
| Memory APIs | `Virtual*FromApp`, `MapViewOfFile3FromApp`, `CreateFileMappingFromApp`; **no RWX pages** (W^X flips on faults) | PS4 guest executables, LLVM JITs, and Switch JIT fastmem all need redesign; fastmem mirroring is impossible in the sandbox (Jadyx uses a page table on every access) |
| Storage | Package dir read-only; LocalState writable but do not assume large free space (rpcs3-xbox puts caches on the drive with most space, normally USB) | 10–30 GB games + compile caches must live on USB and survive cache-wipe recompiles |
| Render-resolution default | Treat **720p internal** as the Series S starting point (gow3_xbox does this for memory; CellBox targets 720p under a memory governor) | Prove frame time at 720p before discussing 1080p; on S, bandwidth — not the 5 GB cap number — is usually first to run out |

**Beginner translation:** on Series S you have a fast-enough CPU for *one* translation layer, a GPU that wants low internal resolution, and a memory pool that punishes keeping two copies of everything. Any design that needs guest RAM + translated textures + a JIT + a Vulkan layer simultaneously is fighting all three at once.

---

## 2. Three goals, three different "best" answers

Keep these separate or every recommendation looks contradictory:

1. **PLAY** — run a game you own on the TV this month → use the existing Xbox emulator where one exists (PS3: rpcs3-xbox; Switch: Jadyx; PS4: essentially only gow3_xbox's single title). Accept its compat list, not the catalog's.
2. **PORT** — take one catalog PC project and make *that build* run as a UWP app → this is what the D-ratings measure. Runtime-first, game-second.
3. **RESEARCH** — learn the translation technology (Cell SPU lifting, GNM→D3D12, NVN→D3D12) → pick the smallest title that exercises the subsystem, with explicit kill criteria.

Privacy/safety note for PLAY: rpcs3-xbox's README discusses opt-in telemetry and asks forkers to remove telemetry code. Before installing *any* third-party .appx, read the repo, prefer building your own package, and never sideload packages from unknown mirrors. The project's own Note 1 says the same about modified downloads.

---

## 3. Shared go/no-go gates (apply before touching a game)

| Gate | Test (standalone on *your* Series S, no debugger) | Pass looks like | Fail = stop and fix underlying layer |
|---|---|---|---|
| G0 Toolchain | UWP x64 skeleton installs via Device Portal, type set to **Game** in Dev Home | 5 GB budget visible (overlay via MemoryManager), clear-screen 60 Hz | Stuck in 1 GB App tier; Win32 (desktop) binary built by mistake |
| G1 Renderer triangle | D3D12 (or Dozen) triangle + resize + suspend/resume | No device-removed; recoverable present loop | PSO-cache API crash; Vulkan loader assumptions |
| G2 Shader pipeline | One guest-style shader: source IR → SPIR-V → DXIL (signed) → PSO → readback matches PC golden | Byte/pixel match, cache hit on 2nd run | Unsigned-DXIL rejection; missing Vulkan extension (see PS4 Dozen verdict) |
| G3 Execute guest code | Tiny authored fixture (never game code first): W^X flip, fault-driven lazy commit (64 KiB granules) | Controlled fault commits page; no RWX anywhere | RWX section rejected; up-front multi-GB commit OOM |
| G4 Memory ceiling | Synthetic pressure to 5120 MiB under a ledger/guard | Caches shrink, app survives, returns to menu | OS termination; "out of host memory" stalls |
| G5 Content on USB | Stream from USB, cache on USB, pull drive mid-load | Graceful error; saves on LocalState intact | Writes to package dir; corrupt cache after wipe |
| G6 Soak | 30 min at 720p with frame-time + memory overlay | Flat memory, P95 inside budget | Slow leak (double-copy growth), shader-compile hitches |

Shiney-X's project is the model student here: phased fixture validations (SPIR-V→HLSL→DXIL, PushData→root constants, authored-IR draw/readback, ELF preflight without executing games). Copy that *method* regardless of family.

---

## 4. PlayStation 3 — Cell is the boss fight

### 4.1 Why PS3 is uniquely hard

`sp00nznet/ps3recomp` (MIT, 625★) [Verified]: static PPU/SPU lifters (Python tools) + runtime libs + HLE stubs. Its own platform table is brutally honest: runtime builds on Windows/macOS/Linux, render backends exist (Win D3D12 / Mac Metal / Linux Vulkan-or-null), but **"Runs a recompiled game, in this tree: Windows yes, macOS no, Linux no"** — the per-game PPU boot scaffold (`ppu_loader.cpp`, `boot_main.cpp`, HLE dispatch) is compiled per title, and downstream game ports carry patches "still on their way upstream." An Xbox port therefore starts behind even the Linux state: you'd write a *fifth* platform column (WindowsStore/AppContainer) for a scaffold that upstream hasn't booted to gameplay off-Windows in-tree.

Cost drivers, in order: (1) **6 SPUs** — 128-bit SIMD units with 256 KB local stores and explicit DMA; SPU-heavy engines (Killzone, Insomniac, Naughty Dog-lineage) are the worst case on a 4+2-core budget whether you lift statically or JIT dynamically. (2) **RSX command stream → D3D12**: no Vulkan shortcut is free (Dozen exists, but see the rpcs3-xbox crash note below). (3) **LV2/PRX surface**: ~300+ syscalls and 100+ libraries per ps3recomp's own challenge table.

### 4.2 The emulator detour that already works

`emelin2004/rpcs3-xbox` (GPL-2.0) [Verified README/uwp docs; results Claimed from dev + opt-in telemetry, builds 0.1.34.73–0.1.35.7, release v0.1.35.14 with .appx]: XAML shell + full RPCS3, **Vulkan renderer running on Mesa Dozen** (`vulkan_dzn.dll` + `dxil.dll`, `vkshim` instead of a Vulkan loader), frames read back (~1 ms) into a D3D11 composition swapchain behind a SwapChainPanel; PPU/SPU LLVM recompilers (6 LLVM threads), lazy 64 KB `sys_vm` commit, pagefile-section shared memory because UWP can't map executable/sparse views. XMB: ~20 s warm / 60 fps with PPU LLVM; cold XMB PPU compile ≈8.5 min. Main remaining crash: games stop with **"Out of host memory" that is actually the Xbox graphics driver rejecting one frame** — i.e., Dozen/D3D12 interop, not your budget spreadsheet, may be the wall you hit. LocalState has little free space in their testing, so caches go to USB (`E:/RPCS3/cache/`); a wiped USB = full recompile next start. Built on Linux with a zig/clang cross toolchain (FFmpeg → LLVM ~2 h → RPCS3 → Mesa 26.2.5 Dozen with two UWP patches) — no Windows PC required, but it is a serious build.

**Catalog overlap check [Verified by comparing tables]:** none of the catalog's 16 PS3 games appears as tested/playable in rpcs3-xbox's October table. The closest, inFamous (first game), runs In-game 10–30 fps GPU-bound — that bodes poorly for catalog title inFAMOUS 2 on Series S via emulation, and says nothing kind about Killzone 2/3 via recomp. Light/non-catalog titles (Minecraft PS3 Ed. 50–57 fps, Driver SF ~59 fps, MvC2 60 fps) show where the emulator route shines on console today.

`coopmatth/CellBox` (GPL-2.0, 1★) is the alternative architecture study: UWP *host embedding* the RPCS3 core on Series S, Game package, **native D3D12 RSX backend** (command-stream translation, display slice, scratch RTs), **pre-baked signed DXIL** (offline GLSL→SPIR-V→DXIL baked into a loadable cache; console never compiles shaders), memory governor targeting 720p (explicitly noting RPCS3's 8 GB PC minimum vs the 5 GB Game tier). Its tree is impressively complete on paper (host versions 1.0.42/1.0.43, frontend library, compile pre-bake tooling) — but I found **no stated "game X runs at Y fps" result** in its README. Treat CellBox as the best public blueprint for a D3D12-native RSX, not as proof of playability. Its signed-DXIL pre-bake idea is directly reusable by a hypothetical ps3recomp-UWP backend.

### 4.3 PS3 per-game verdicts (Series S)

"Recomp→Xbox" = bring the catalog PC recomp to UWP. "Play today" = emulator-route expectation [Inference from rpcs3-xbox's table + title weight; untested unless stated].

| Game (catalog PC state) | Recomp→Xbox | Series S reading & first gate |
|---|---|---|
| Armored Core 4 (D3D11, Not stated) | D4 | Least-bad PS3 recomp: D3D11 host + mission-contained maps dodge the PSO-cache and streaming problems. Play-today via emulator: plausible light-test candidate, unproven. Gate: run ps3recomp host scenes on UWP before AC4 code |
| Armored Core: For Answer (D3D11, Not stated) | D4 | Same, bigger/faster (high-speed loads stress DMA). Do AC4 first; shared FromSoftware-era engine knowledge transfers only partially |
| Bakugan: Battle Brawlers (ps3recomp D3D12, In-game arena) | D5 | Small arena helps rendering, not the missing runtime. Emulator: try-it-and-see tier |
| Demon's Souls ×2 (ps3recomp D3D12, In-game to 1-1) | D5 | The dream target and the resource sink. SPU+streaming. If your goal is *playing* Demon's Souls on Series S this year, neither route is honest yet |
| Drakengard 3 (Intro only) | D5 | Nothing to port until PC reaches sustained gameplay; musou crowds later |
| God of War: Ascension (In-game ~13 fps **on PC**) | D5 | Fails the first rule: don't port slower-than-real-time PC builds to weaker hardware |
| inFAMOUS 2 ×2 (Metal/Vulkan, In-game) | D5 | Open world + no Windows-first host in-tree. Emulator evidence (inFamous 1: 10–30 fps GPU-bound) suggests S will struggle; motion/TouchPad heritage is PS4-era, not here |
| Killzone 2 (In-game level 1) | D5 | Canonical SPU showpiece; deferred-rendering bandwidth at 720p is the whole project |
| Killzone 3 (In-game) | D5 | As KZ2; one downstream runs via Proton per ps3recomp README — irrelevant layers for UWP |
| Killzone HD (In-game) | D5 | Remaster indirection: you'd port a PS3 port of a PS2 game while XBSX2/PS2 thinking exists |
| PS All-Stars Battle Royale (In-game) | D5 | Arena scope can't amortize Cell runtime. A *second-wave* target only |
| Ratchet & Clank: Tools of Destruction (In-game) | D5 | Insomniac's SPU-centric engine; streaming planets |
| Shadow of the Colossus PS3 (boot only) | D5 | Worst version to choose: PS2 (emulator), PS4 (native-exec pattern) both dominate it |
| Soulcalibur II HD Online (Not stated; D3D12 available) | D5 today → D4 *after* a UWP runtime exists | **Designated first PS3-recomp target**: fixed arenas, 60 Hz logic easy to verify, no streaming world. Don't let "HD Online" pull netcode into scope |
| Tony Hawk's Project 8 (Not stated) | D5 | Open-world + Lua mod API sandbox audit |
| White Knight Chronicles II (In-game) | D5 | Huge JRPG data + early runtime |

**If you insist on PS3 research (in order):** ① build rpcs3-xbox from source and profile one light title you own on your S (learn Dozen failure modes) → ② replicate CellBox's signed-DXIL pre-bake in a toy D3D12 app (G2 gate) → ③ boot ps3recomp's `ps3recomp_host` scenes (no game) under UWP → ④ only then Soulcalibur II HD menus→one stage at 720p. Kill criteria: SPU DMA throughput <50% of PC host-scene baseline, or any design requiring runtime shader compilation on console.

---

## 5. PlayStation 4 — same CPU, hostile everything else

### 5.1 Two fundamentally different Xbox strategies

**Route A — single-game native execution (catalog's model).** PS4 eboot is x86-64: run guest code directly, replace Orbis libraries (kernel, GNM driver, libc, FIOS, audio, pad), translate GNM/PM4 command buffers to Vulkan/D3D12 and GCN shaders via SPIR-V→DXIL. bbport [Verified README] is explicit: *not* shadPS4, Wine+DXVK-for-one-game, eboot converted offline to a flat image with PS4 libc/libSceFios2 linked in, own renderer/shader translator rewritten from shadPS4 roots, PC memory model keeps hot data in VRAM. That last assumption **breaks on Series**: there is no separate VRAM — guest RAM, mirrored blocks, and GPU copies all bill the same 5120 MiB. The proven Xbox adaptations (from doc 01's audit) are: `Cosmo/gow3_xbox` — Kyty-lineage pager, **720p default because 4K spills ~450 MiB to swap**, shader precompile (≈3 min for ~7,000 shaders) vs mid-gamecompile pop-in choice; and KytyPS5's Xbox fork as the D3D12 blueprint (64 KiB commit-on-touch guest memory, swap file, texture-detail-for-memory options, FL11.0/SM6.4 ceilings, draws the console can't do — e.g. tessellation — are skipped).

**Route B — general emulator (shadPS4) with a new D3D12 backend.** Two public attempts, both honest that games don't run yet:
- `AmitAmit99/shadPS4-xbox` (branch `xbox`, base tag `Shadlix-shadPS4-2026-10-12-11f2e97…`, KytyPS5 fork cited as MIT blueprint): Phase 1 shell (no Qt/SDL window, CoreWindow, `*FromApp` + W^X fault-switching in `address_space.cpp`, NT-API replacements, **import check: 404 Xbox-missing imports across 16 DLLs in the baseline exe**), Phase 2 D3D12 renderer (`spirv_to_dxil` + Kyty patch + SDK `dxil.dll` signing; notes `renderer_vulkan` ≈43 files/11k lines and 38 files elsewhere include Vulkan types — the shared/Vulkan split is mandatory first surgery), Phase 3 make **UFC 3 (CUSA06534)** playable. Status 2026-10-14: plan + `spirv_to_dxil.dll` built + baseline desktop exe built-not-run. **Do not conflate UFC 3 (their test target) with catalog title UFC 4.**
- `Shiney-X/xbox-series-d3d12` (Series S-first, shadPS4 baseline **v0.18.0 commit e3ce810…**): furthest *foundation* validation [Claimed, phased docs]: VM/exec/aliases/5 GiB, D3D12/DXC/present/suspend, USB browsing + `param.sfo`/`icon0.png` on console, GpuCommandSink DMA preview, SPIR-V→HLSL→DXIL, PushData→root constants, real `EmitSPIRV` IR→dispatch/draw readback, ELF/SELF preflight, authored-ELF fixture execution. Explicitly: **no game shaders translated, full core not compiled, no boot button, does not run games.**
- **Dozen verdict (shadPS4-specific) [Verified experiment in XBOX_PORT.md]:** Mesa e24dc5bd Dozen crashed vulkaninfo on PC GPUs and on WARP exposed only Vulkan 1.2 without `VK_KHR_push_descriptor` / `VK_EXT_robustness2`, while shadPS4 asserts Vulkan 1.3 + both extensions at startup. Conclusion there: Dozen-under-shadPS4 ruled out *at that Mesa commit on those devices*. This does **not** contradict gow3_xbox/RPCS3-xbox using Dozen successfully — their Vulkan consumers ask for less (and carry their own Mesa forks/patches). Lesson: "Vulkan→Dozen" is a per-renderer extension negotiation, not a universal solvent.

### 5.2 PS4 per-game verdicts (Series S)

Route B benefits every row *eventually*; Route A is the only path with an Xbox-playable precedent today. Internal resolution expectation on S: **720p, 30 fps first** for anything 3D.

| Game (catalog PC state) | Diff. | Series S plan / gate |
|---|---|---|
| God of War III Remastered (In-game PC; Xbox fork alpha) | **D1** | Only D1. On your S: install/build the Xbox fork, stay at its 720p default, use its precompile step; verify 30-min soak + shader-cache persistence yourself — treat any 4K/60 claim as Series X marketing until measured on S |
| Odin Sphere Leifthrasir (Not stated) | D4 | **Research target #1.** 2D sprite workloads minimize GNM/tiling pain and memory mirroring. Gate G2 with its 2D shaders; target 1080p *display*, 2D assets are light |
| Dragon's Crown Pro (Not stated) | D4 | Twin of above (same Vanillaware profile); pick whichever PC build you can compile cleanly first — buildability decides |
| Crash Team Racing Nitro-Fueled (Playable; Vulkan+D3D11) | D4 → D3 *iff* D3D11 path audits clean | First audit whether its D3D11 renderer is a real guest-GNM translation or a present-blit after Vulkan. True D3D11 = best PS4 3D candidate; split-screen suits console; cut P2P MP |
| WipEout Omega Collection (In-game, gow3_pc framework) | D4 | Best *framework-reuse* bet: closed circuits, deterministic loads, sibling already on Xbox. 720p/60 is the honest S goal; two games (HD/2048) = scope-control to one |
| EA Sports UFC 4 (Playable; renderer unlisted) | D4 | Arena scope is attractive; renderer audit is gate zero. Note Amit's project targets UFC **3** — shared EA-engine lessons may transfer, binaries won't |
| Kamen Rider: Memory of Heroez (Not stated) | D4 | Arena action; shadPS4-runtime heritage means Route B may reach it before a hand port is justified |
| Fist of the North Star: Lost Paradise (Not stated) | D4 (heavy end) | like a Dragon (RGG) city scope on a bbport base; mini-game/codec surface area is the hidden cost |
| Bloodborne ×16 forks (Playable on PC, experimental; full playthrough unverified even on PC per bbport README) | D5 | Research program, not a port: PC memory model (VRAM mirroring with 20 s/60 s eviction) must become a unified-memory ledger; FSR 4/DLSS/frame-gen features are PC-GPU gloss, not your path. Any S goal starts "720p, 30 fps, Central Yharnam soak without OOM" — nobody public is close |
| Gravity Rush 2 (In-game) | D5 | Open-world streaming + gyro remap (pad-only design work) |
| inFAMOUS Second Son ×2 / First Light (In-game) | D5 | Open world, touchpad/motion substitutions, particle bandwidth — S-hostile |
| Driveclub ×2 (In-game) | D5 | Streaming racer; wheel FFB meaningless in UWP pad model |
| Shadow of the Colossus PS4 (In-game) | D5 | Choose PS2-via-emulator for playing; this version's frame-gen PC features don't transfer |
| The Last Guardian ×2 (In-game) | D5 | Streaming + fur/AI perf already delicate on PC |
| Astrea / Atelier Ayesha DX / Atelier Ryza / SaGa Emerald Beyond / Tales of Symphonia R. (psport, Linux, In-game/Not stated) | D5 | Blocker is the *starting point* (1★ general Linux layer, no Windows build), not the games — several are light and some have official PC releases outside the catalog. Revisit only if psport grows a Windows host or Route B matures |

**Milestone ladder (Route A, Odin Sphere-sized):** PC build reproducible → import-check clean vs WindowsApp.lib → shell boots to first GPU submission with log-only renderer on console (Amit Phase 1 checkpoint) → one signed-DXIL draw (G2) → title screen at 720p → memory ledger + texture eviction under 5120 MiB → 30-min soak on S. Estimated [Inference]: experienced dev 3–6 months for a 2D title *reusing* Kyty/gow3 patterns; a beginner should treat PS4 as a second-year project.

---

## 6. Nintendo Switch — the emulator already won (for playing)

### 6.1 Jadyx reality on Series S

`JulianDr14/jadyx` v0.3.9.0 [Verified README/compat doc]: Eden fork, **native D3D12 backend modeled on Eden's Vulkan backend (FL 11.0, SM 6.4, no Agility SDK)**, guest shaders SPIR-V→DXIL via patched Mesa `spirv_to_dxil` + `dxil.dll` signing, disk shader cache, PSOs built on draw and released when idle (exactly the Dev Mode PSO-cache workaround), placeholder `*FromApp` guest memory with **no fastmem** (page-table on every guest access), and a memory guard that shrinks caches as 5120 MiB approaches. Series S community reports in its compat doc [Claimed]: Pokémon Legends: Arceus 30 fps stable, Yo-kai Watch 4++ 27–30 fps open areas (minor distortions), plus non-catalog 60 fps reports (Yoshi's Crafted World ~3.45 GB RAM, Persona 4 Golden, Diablo III, Hades II) and drops in heavier titles (Bayonetta 2: 60→30–40 in combat). Catalog-title data point that matters most: **Zelda TotK "renders without graphical errors, then hits the memory wall" on Series X** (PC reaches open world at 30 fps) — on your S, with less bandwidth headroom under the same 5120 MiB cap, plan accordingly. Mario Odyssey is listed on Series X (45–50 fps open, 60 enclosed); no S claim was found — don't extrapolate dishonestly.

### 6.2 Why catalog recompilations don't transfer (yet)

Each catalog Switch project assumes a desktop host that UWP isn't: **TotK Recomp** (MIT, ~4.6k★, "playable Win/Linux, bugs/crashes expected") requires **Vulkan 1.3 + `VK_EXT_external_memory_host`**, x86-64 SSE4.2, ~36 GiB free during setup (20 GiB after), builds the game from your files via a setup executable, supports ExeFS patch *rebuilds* and optional NVIDIA DLSS. `external_memory_host` (GPU reading host-mapped guest memory in place) is precisely the kind of zero-copy trick the AppContainer/`FromApp` + Dozen stack is least likely to give you; the on-PC self-build installer model also has no UWP equivalent. **LASRecomp** (~2.1k★) targets the small Link's Awakening — catalog rows claiming it for Arceus/Let's Go need a from-scratch audit of what code actually exists vs aspirational naming. **mk8-recomp** builds on suyu's AOT+HLE (emulator heritage, license NONE detected — do not redistribute derivatives casually). **nxrecomp** is an 8★ young runtime. **nxnative** (MIT, ~11k★) is Apple-only by design (NSO→IPA, NVN→Metal): its Horizon HLE ideas are study material, its code path is not an Xbox route. No Switch-recomp-to-UWP precedent was found (GitHub search 2026-11-04), consistent with doc 04.

### 6.3 Switch per-game verdicts (Series S)

| Game (catalog PC recomp state) | Recomp→Xbox | On your S today / honest route |
|---|---|---|
| Pokémon Legends: Arceus (Not stated) | D5 | **Play-via-Jadyx candidate**: 30 fps stable on S [Claimed]. Recomp port has no advantage to chase yet |
| Yo-kai Watch 4++ (In-game) | D5 | Jadyx on S 27–30 fps with minor distortions [Claimed] — playable-with-asterisks beats a D5 port |
| Pokémon Let's Go Eevee/Pikachu (In-game) | D5 | Jadyx lists Let's Go 60 fps stable on *Series X* only — test on your S before believing; motion-catch remap exists in emulator-land already |
| Super Mario Odyssey (In-game) | D5 | Jadyx Series X numbers exist; S unproven. Kingdom streaming + texture double-copy vs 5120 MiB is the shared enemy of both routes |
| Mario Kart 8 Deluxe (Not stated, Linux/Android) | D5 | Jadyx compat lists *Mario Kart 8 (Wii U/32-bit builds)* on X — don't confuse with Deluxe binaries. (Mario Kart Wii is D1 via a different route entirely, doc 04) |
| Metroid Prime Remastered (Not stated) | D5 | No S emulator data found in this pass; nxrecomp is the youngest toolchain here |
| Zelda: Tears of the Kingdom (In-game PC-"playable") | D5 | Hard no for S by either route today: emulator OOMs on X; recomp needs Vulkan-1.3-host-memory + 20 GiB install + rebuild model. Revisit if Jadyx's memory work or a D3D12-native recomp backend lands |
| Smash Bros. Ultimate (Not stated, DX11) | D5 | DX11 renderer is the *only* friendly attribute; content scale + local-wireless netplay assumptions vs sandbox dominate. 4-player local is the dream use-case — in a later era |
| Fire Emblem Engage (archived, first battle) | D5 | Archived upstream; no route |
| Tomodachi Life: Living the Dream (no Windows host) | D5 | Two non-Windows experiments; nothing to bring over |
| Xenoblade Chronicles 2 (Not stated, 6★) | D5 | Largest JRPG scope; earliest code |
| Devil May Cry — Switch (nx2apk, repo gone) | **BX** | Blocked: repository gone *and* it was an Android tool, not a Windows port. (PS2 DMC in doc 04 is a separate D5) |

*Coverage note: 12 rows, 13 catalog pages — Let's Go Eevee and Pikachu are separate catalog pages sharing one row (same project, same verdict). Together with §4.3 (16 PS3) and §5.2 (15 rows covering 20 PS4 — one combined inFAMOUS row, one combined 5-title psport row), all 49 in-scope game pages are covered.*

**If Switch is your passion:** contribute compatibility reports/patches to the emulator route on real Series S hardware (genuinely scarce data — almost everything above is X-reported or single-tester), and study `src/video_core/renderer_d3d12/` as the best public FL11.0/SM6.4 renderer education available. A recomp-to-UWP attempt should not be pitched to yourself as "playing TotK on S" — the evidence says even X can't hold it in memory yet under emulation, and the recomp removes CPU/JIT overhead, *not* the texture double-copy that creates the wall. [Inference: a static recomp with texel-level control *could* eventually beat that wall by avoiding a general texture cache — that is a research hypothesis, not a plan with a date.]

---

## 7. Exact starting points (repos / branches / baselines)

| Purpose | Repo · branch/baseline [Verified] | License | Use it for |
|---|---|---|---|
| PS3 recomp toolkit | [`sp00nznet/ps3recomp`](https://github.com/sp00nznet/ps3recomp) · `master` | MIT | `ps3recomp_host` scenes first; per-game scaffold awareness |
| PS3 emulator on Xbox | [`emelin2004/rpcs3-xbox`](https://github.com/emelin2004/rpcs3-xbox) · `main`, rel. [**v0.1.35.14**](https://github.com/emelin2004/rpcs3-xbox/releases/tag/v0.1.35.14) (.appx); UWP notes in [`uwp/README.md`](https://github.com/emelin2004/rpcs3-xbox/blob/main/uwp/README.md) | GPL-2.0 | Playing light titles; Dozen/vkshim + lazy-commit patterns; build-from-source |
| PS3 D3D12-native study | [`coopmatth/CellBox`](https://github.com/coopmatth/CellBox) · `main` (host 1.0.43) | GPL-2.0 | RSX→D3D12 design + signed-DXIL pre-bake; **no proven game state** |
| PS4 single-game upstream | [`deadinside28/bloodborne_pc`](https://github.com/deadinside28/bloodborne_pc) · `master` (bbport 0.7+) | GPL-2.0 | Understanding Route A architecture (PC-first) |
| PS4 general-emu attempt A | [`AmitAmit99/shadPS4-xbox`](https://github.com/AmitAmit99/shadPS4-xbox) · branch `xbox`, base tag 2026-10-12 `11f2e97…`; plan in [`XBOX_PORT.md`](https://github.com/AmitAmit99/shadPS4-xbox/blob/xbox/XBOX_PORT.md) | GPL-2.0 (Kyty excerpts MIT-noticed) | Phase plan, import-check tooling, Dozen negative result |
| PS4 general-emu attempt B | [`Shiney-X/xbox-series-d3d12`](https://github.com/Shiney-X/xbox-series-d3d12) · `main`, baseline shadPS4 **v0.18.0 `e3ce810…`** | GPL-2.0 | Series S validation method (Phases 0–5C fixtures) |
| PS4/5 Xbox blueprint | `Cosmo/KytyPS5` Xbox fork + `Cosmo/gow3_xbox` (doc 01 audit) | per-repo (check) | Pager, texture downgrade, shader precompile UX, FL11.0 limits |
| Switch emulator on Xbox | `JulianDr14/jadyx` · rel. **v0.3.9.0** | GPL-3.0-lineage (check files) | Playing/testing on S; D3D12 renderer study |
| Switch recomp flagship | `valentderah/totk-pc-recomp` | MIT | PC-only today; requirements audit (VK1.3 + external_memory_host) |
| Switch recomp toolkits | `peiikai/LASRecomp` · `dougchansan/mk8-recomp` (lic. NONE) · `drakolordx7/nxrecomp` (GPL-3.0) · `seedds/nxnative` (MIT, Apple) | as listed | Study, not Xbox starting points |

---

## 8. Recommended 90-day plan for *you* (beginner, Series S)

**Days 1–14 — Prove your pipe.** POC from `poc/README.md` at 720p on your S (G0–G2 gates) + install/build one *existing* Xbox app from source (rpcs3-xbox *or* Jadyx) and log frame times/memory on titles you own. Exit: you can ship, install, and measure without the debugger.

**Days 15–45 — Pick ONE lane:**
- *PS3 lane (play + learn):* rpcs3-xbox compat testing on S for light titles; reproduce its Dozen build; write up the "out of host memory" failure on one title with logs. This is publishable, scarce Series S data.
- *PS4 lane (research):* PC-build Odin Sphere *or* Dragon's Crown catalog port; run an Amit-style import check; stub renderer to first-GPU-submission log inside a UWP shell on PC. Exit = Phase-1 checkpoint, not pixels.
- *Switch lane (play + report):* Jadyx S-compat reports for 3 catalog-overlap titles you own (Arceus, Yo-kai, Let's Go) with memory-ledger screenshots. Exit = three honest S data points where today there are X reports.

**Days 46–90 — One gate deeper, with kill criteria.** PS3: signed-DXIL toy (G2) or host-scene boot. PS4: signed-DXIL single draw from a *real* guest shader. Switch: replicate a Jadyx renderer test from `tools/xbox/tests/`. If a gate fails twice for the same root cause, write it up and switch lanes — that's progress, not defeat, on D5 terrain.

**You said you'll pick the N64 title yourself** — keep that as your parallel "win" track (doc 04 D1/D2 family) so the hard families don't block your first finished console build. Tell me the title + that you own the cartridge, and I'll write its exact branch-by-branch build order the same way.

---

## 9. Family-specific troubleshooting additions

| Symptom | Likely cause (family) | Test |
|---|---|---|
| "Out of host memory" mid-game (PS3 emu) | Driver-rejected frame through Dozen, misreported as OOM [Claimed: rpcs3-xbox] | Drop to 720p, clear shader cache, check their issue tracker before redesigning budgets |
| 8+ min first boot, fast later (PS3 emu) | PPU LLVM compile, cached on USB | Don't wipe USB; caches are the product |
| App won't start, no log (PS4 Route A/B) | Desktop-only import (baseline shadPS4 exe had 404) | Import-check script on *every* build |
| RWX commit rejected / W^X faults (PS4/PS3 JIT) | Mapping whole guest section executable-writable | Split views; fault-switch write↔execute; lazy 64 KiB commit |
| Vulkan init asserts on console (PS4) | Renderer demands VK 1.3/push-descriptor/robustness2 beyond Dozen build | Negotiate per-renderer (Amit experiment); consider D3D12 backend instead of forcing Dozen |
| Renders clean, then OOM in heavy area (Switch) | Texture double-copy vs 5120 MiB (TotK pattern) | Lower internal res, watch ledger; if emulated-memory + texture cache > ~4.2 GiB, no setting saves you — need eviction work |
| Shader hitches after cache wipe (all) | PSO building on draw; no pipeline-library caching available | Pre-bake/precompile step with progress UI (gow3 model); keep DXIL, rebuild PSOs at boot in parallel (Jadyx model) |
| Series X report says 60 fps, your S doesn't | Bandwidth/CU gap under identical caps; X-tested ≠ S-tested | Re-baseline at 720p with P95 frame times; never cite X numbers as S expectations |

---

*Evidence basis: docs 01 + 04 audits (2026-11-04) plus GitHub API reads of ps3recomp README, rpcs3-xbox README + uwp/README + releases, CellBox README, shadPS4-xbox XBOX_PORT.md, xbox-series-d3d12 README/phase docs, bbport README, totk-pc-recomp README, Jadyx README + xbox_compatibility.md (86 lines, grepped for all catalog titles), and toolchain star/license metadata for LASRecomp/mk8-recomp/nxrecomp/nxnative. Nothing was built or run; fps/memory figures attributed to their projects as [Claimed].*
