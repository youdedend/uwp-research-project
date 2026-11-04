# 01 — Feasibility, Sources & Case Studies (A–D)

Reviewed live 2026-11-04. [Verified]=in docs/code at review time · [Claimed]=repo/community asserts, not build-tested here · [Inference]=engineering judgment. **I did not compile any repo nor run code on a console.**

---

## A. Feasibility verdict and assumptions

### A.1 Verdict for *your* project as specified

**Inputs:** no game in mind, "learn everything", target **Series X|S Developer Mode (personal/testing)**, beginner programming level.

**Verdict: FEASIBLE as a learning project; NOT YET ASSESSABLE as a port.**

There is no codebase to assess, so any claim like "your game will run at 60 fps with D3D12" would be invented. The *feasible* project is a staged learning path:

1. **Stage 0 (weeks):** Windows PC + Visual Studio UWP toolchain → deploy a tiny original SDL/D3D sample to the Series console in Dev Mode. Proves toolchain, packaging, input, display.
2. **Stage 1:** Pick a real codebase you own or that is permissively licensed (e.g. write a small SDL game, or study BurgerDoom's structure — don't start with an emulator).
3. **Stage 2:** Run the compatibility matrix (Section D) against that codebase *before* promising a port.

Starting with KytyPS5/Jadyx-class projects (custom D3D12 renderers, JITs, SPIR-V→DXIL translation, guest-memory pagers) as a beginner is **not feasible** as a first port — they represent months-to-years of specialist work by their authors, and their READMEs say "experimental/beta" even so.

### A.2 The two Xbox worlds (do not mix them)

| | **Developer Mode / UWP** (your target) | **GDK / GDKX — commercial** |
|---|---|---|
| Console | Retail Series X\|S / One switched to Dev Mode | Dev kits / registered test hardware |
| App model | UWP AppContainer, MSIX/APPX, **x64 only** [Verified: MS system-resource page] | GDK title (Win32-derived), ERA partition on console |
| Who can use | Anyone with a MS dev account (personal testing/sideload) | Approved ID@Xbox / managed partners, NDA |
| Store publishing | **UWP games are no longer accepted in the Xbox Store** [Verified: MS Windows game dev guide banner]; UWP itself "no longer under active development" | This *is* the publishing route (certification, Partner Center) |
| Docs in your list | Community wikis + archived MS UWP-on-Xbox pages | devdocs.xbox.com, Unity/Defold Xbox pages, Xbox Live tools |
| Resources | Capped (see A.3) | Near-full hardware (exact budgets under NDA — not quotable here) |

**Consequence:** Every Unity/Defold/The-Forge/Xbox-Live claim must be read as *commercial-route* information. It teaches concepts, but its build/packaging steps will **not** produce a Dev Mode sideloadable package.

### A.3 Verified platform facts (Microsoft)

From Microsoft Learn, *System resources for UWP apps and games on Xbox One* (now under previous-versions; fetched 2026-11-04 — treat as last-published UWP guidance, re-verify on device):

- Foreground memory: **Apps 1 GB · Games 5 GB**; background 128 MB; games suspend/terminate in background. Limits don't apply under the VS debugger. [Verified]
- CPU: Apps share 2–4 cores; Games get 4 exclusive + 2 shared. GPU: Apps ~45% share; Games full available GPU cycles. [Verified]
- DirectX on **Series X|S (UWP): Apps and Games — DirectX 11 and DirectX 12 with Hardware Feature Level 11.0.** On Xbox One, UWP *Apps* are D3D11 FL10.1 only, Games add D3D12 FL11.0. [Verified]
- **All Xbox UWP apps/games must target x64.** [Verified]
- UWP game guide retains D3D12 samples/templates/DirectXTK12 pointers, while warning UWP is not under active development and UWP games are no longer accepted in the Xbox Store. [Verified]

What official docs do **not** give you (don't let community posts fill these in as "official"): GDKX D3D12 extensions, exact Series GPU feature tiers for UWP beyond FL11.0, sustained clocks under UWP, or any guarantee about community translation layers. Jadyx/KytyPS5 document *empirical* console ceilings (e.g. Shader Model 6.4, no Agility SDK, 5120 MiB) — valuable, but [Claimed]/measured-by-them, not MS commitments.

> ⚠️ "5 GB" is *unified*: CPU + GPU resources share it. Every heavy case study below hits this wall — it is the single most important Dev Mode constraint.

### A.4 The source-code gate (applies to any future game)

| You have… | Realistic options |
|---|---|
| **Full source + rights + assets you may ship** | Porting assessment can proceed (matrix in D). |
| **Open-source game (check license)** | Port *if* license allows modification/redistribution and dependencies are portable. GPL ports must stay GPL, etc. |
| **Compiled game only (.exe, installed title)** | **No port.** You cannot rebuild for a new app model/GPU API, cannot fix Win32-only calls, cannot re-sign as UWP. Options are: play it on its native platform, stream it (e.g. Moonlight-class UWP clients — a different project), or reimplement a *new* original game. Reverse-engineering/decompilation is a years-long specialist field with its own legal constraints — out of scope as a "porting shortcut", and this handbook gives no instructions for obtaining/decrypting game dumps, keys, firmware or BIOS files. |
| **Engine project (Unity/Godot…)** | Depends entirely on that engine's *UWP* export status for your exact version — not its GDK Xbox support. See D/H. |

### A.5 Assumptions & missing information

Assumed: retail Series X *or* S (state which — S has materially less GPU/memory bandwidth headroom inside the same 5 GB UWP cap), Windows 10/11 PC available, ability to enroll in Dev Mode, personal use only. **Still needed before any real port verdict:** exact codebase + license, language/engine versions, current renderer/API, dependency list (middleware, codecs, JITs, plugins), asset formats/sizes, networking needs. See the intake checklist in `03-…` §L.

---

## B. Source inventory and review (grouped by type)

Full one-line evidence: [`evidence-table.md`](evidence-table.md). Below: what each source *is*, what it teaches, limits, relevance to Series Dev Mode learning.

### B.1 Official Microsoft (1–3, plus 7 & 29 technically)

**1. Microsoft Game Development hub** — Marketing/onboarding for GDK + ID@Xbox + PlayFab. Teaches the *commercial* landscape (programs, engines, services). Limit: no Dev Mode/UWP technical content. Relevance: orientation only.

**2. devdocs.xbox.com (home)** — Current official *GDK* documentation: onboarding, GDK setup, porting paths, services, publishing. Explicitly targets Series/One/PC via GDK. Limit: GDKX/console specifics are NDA-gated ("NDA Topics" in nav) — I cannot verify gated claims and neither can you without enrollment. Relevance: authoritative for the commercial route; *not* a Dev Mode UWP manual.

**3. Useful-links page** — Portal directory (Partner Center, GDK downloads, publisher guide). Last modified 2026-11-02 per page. Teaches where commercial developers operate. Relevance: bookmark if you ever go ID@Xbox; skip for Dev Mode coding.

**7. microsoft/DirectXTK (MIT, actively maintained)** — Helper classes for **Direct3D 11** C++ (sprites, models, audio via XAudio2, GamePad, loaders) for Win32/Xbox One/UWP, VS2022/2026. **Common trap: this is not the D3D12 toolkit.** D3D12 work needs the separate *DirectXTK12* (not in your list). Relevance: genuinely useful if you choose the (often smarter) D3D11 UWP path; misleading if cited as D3D12 evidence.

**29. microsoft/xbox-live-developer-tools** — Official Xbox Live service *tooling* (test accounts, sandboxes, resetting player data). README requires ID@Xbox or Creators Program enrollment. Limit: useless for offline Dev Mode homebrew that has no title ID/sandbox. Relevance: commercial-services learning only.

### B.2 Engine/vendor (4–6)

**4. Unity for Xbox** — Requires Unity Pro + registered Xbox developer status + GDK packages. [Verified from page] This is the GDK route. It does **not** document the old Unity→UWP export to Dev Mode (Unity's UWP platform is a separate, legacy workflow — community link #30 points to guides; check your exact Unity version's UWP support status before believing any tutorial). Relevance: if you later choose Unity *commercially*; otherwise conceptual.

**5. Defold Xbox manual** — One page: become approved Xbox dev → request Defold Xbox access via middleware page → gated extension/tools/NDA docs. No public Dev Mode path is documented. Relevance: proves "engine supports Xbox" ≠ "you can sideload it tonight."

**6. ConfettiFX/The-Forge (Apache-2.0 for public platforms)** — Professional cross-platform C++ framework (D3D12/Vulkan/Metal backends, resource loader, animation, ImGui UI; no physics/networking/sound). **Console backends (Xbox/PS/Switch) are commercial-licensed to accredited developers on request** [Verified: README]. Relevance: excellent *D3D12 architecture study material* on PC (it even uses D3D12MemoryAllocator/VMA internally); **not** a Dev Mode Xbox SDK you can download.

### B.3 Game/emulator ports to UWP (8–18) — case studies only

Treated in depth in Section C. One-line truths:

- **8. KytyPS5 (GPL-2.0)** — PS5 translation layer fork with the most meticulously documented Xbox delta (`XBOX_CHANGES.md`, one commit per topic). Custom D3D12 renderer + lazy guest-memory pager + WinUI launcher. Best-in-set teacher for *large-system* UWP engineering. Needs user-supplied games; experimental.
- **9. gow3_xbox (GPL-2.0)** — PS4-remaster native loader (runs guest x86-64 code directly, W^X via *FromApp APIs) with Vulkan→Dozen→D3D12 graphics. Superb dev-log in `xbox/README.md` (including honest "not playable yet" milestones and measured 5,120 MiB budget). Series-only, alpha.
- **10. uncharted_xbox (GPL-2.0)** — ⚠️ Name overpromises: README, requirements (Vulkan 1.3, 6 GB VRAM) and releases all describe the **Windows PC** port; I found an `xbox/` skeleton but **no Xbox documentation or releases**. Treat as "PC port + unfinished Xbox branch", not evidence of a working Xbox build.
- **12. dusklight-uwp (CC0-detected; ARCHIVED)** — Twilight Princess decomp (Dusklight/Aurora). README now states development **discontinued**. Study value: how UWP forks of decomp projects stall (upstream churn + tiny maintainer pool). Do not start from an archived fork expecting support.
- **13. WWHD-UWP (MPL-2.0)** — *Source overlay* (not a standalone tree) pinned to an upstream recomp commit; needs external tooling/deps; generates code on-console from user media. Vulkan via Dozen, SDL3-UWP. Teaches overlay-maintenance and on-device build trade-offs.
- **14. jadyx (GPL-3.0)** — Switch emulator (Eden fork) with the **only other hand-written native D3D12 backend** in the set, plus the deepest public Xbox docs (`docs/xbox/`: build, GPU, CPU, texture memory, performance). Beta; no keys/firmware/games included (bring your own legally — no instructions here).
- **15. BurgerDoom (MIT)** — 3DO Doom source port + thin UWP adaptation (SDL2-UWP, root AppxManifest). **The only beginner-scale game port in the list.** Its UWP diff is small enough to actually read in an evening. Note its manifest requests `runFullTrust`/`broadFileSystemAccess`/`expandedResources` — understand capabilities before copying them (see §I).
- **16. 2ship2harkinian-uwp** — Majora's Mask decomp port. Rendering is **D3D11 or OpenGL (default)** — a standing counterexample to "everything Dev Mode is D3D12."
- **17. melee-UWP (YTReviveMe)** — **404 on 2026-11-04.** Do not cite it. The discoverable successor `JYRS20/Melee-UWP` is an experimental overlay explicitly stating build integration is incomplete. Lesson: link rot is normal in this scene; always re-verify.
- **18. switch-gdx (GPL-2.0)** — LibGDX backend: Java/Kotlin bytecode → C++ (Clearwing VM), targets Switch homebrew + Xbox UWP. Real shipped ports listed (Mindustry etc.). Limits: GLES2-class, no GL30, sockets broken, Clearwing runtime gaps. The set's only Java path — and it's transpilation, not a JVM.

### B.4 Graphics/API layers & libraries (11, 19, 23–28)

- **11. mesa_ai_slop_version** — ⚠️ Self-described AI-written Mesa/Dozen fork, 0 stars, no releases. It *is* load-bearing (gow3_xbox's credits consume its `vulkan_dzn.dll`), which is exactly the risk: unreviewed shader-compiler changes (recent commits lower 16-bit ops for FL11.0-era hardware). Study the *idea* (Vulkan-on-D3D12); prefer a pinned, reviewed Mesa commit for anything you ship, and diff AI commits ruthlessly.
- **19. SternXD/D3D12MemoryAllocator** — Byte-identical fork of GPUOpen's D3D12MA (MIT). The *library* is excellent and used by KytyPS5's renderer; the *fork* adds nothing. Consume upstream (or via vcpkg) and pin a version.
- **23. SDL3-uwp (Zlib)** — The set's workhorse. Key docs inside: `README-winrt.md` (UWP: VS, CoreWindow swapchain, ANGLE GLES2, XInput limits—in particular UWP only sees "Xbox-compatible" controllers) vs `README-gdk.md` (GDKX needs licensed libs). Versioned branches + `SDL-UWP.zip` releases = the most maintainable dependency here.
- **24. dawn-uwp** — WebGPU (Dawn) UWP-compat fork at "early basic compatibility" stage (single compat commit; `uwp/` only holds libuwp binary). Upstream Dawn→D3D12 is production-grade *on desktop*; the UWP port completeness is **unproven**. Interesting future path (WGSL instead of hand D3D12), risky today.
- **25. mesa-uwp** — The serious Mesa-UWP line (aerisarn/worleydl heritage per #21/#30 credits): needs a UWP-capable Meson fork, `--backend=vs --uwp`, `_XBOX_UWP` defines. Provides three distinct things people conflate: (a) Gallium OpenGL-on-D3D12, (b) Dozen Vulkan-on-D3D12, (c) `spirv_to_dxil` shader translation. Each has different maturity—state which you mean.
- **26. libuwp (Zlib, 28 KB)** — Screen/window refs, bundle paths, DLL-load workaround, ROM picker helper, event pump, gamepad callbacks. Tiny, readable, reusable — the ideal first "copy the pattern" library.
- **27. xbox-swap (GPL-3.0, 59 KB)** — File-backed swap + o1heap to allocate "beyond 5 GB." Understand what this is: *paging cold CPU memory to disk under a hard commit cap*, not extra RAM. It trades stutter/OOM risk. KytyPS5/gow3 independently implement similar pagers — a pattern born of desperation for emulator guest memory, **not** something a normal game should need (budget instead).
- **28. angle fork** — ANGLE translates GLES→D3D11 on Windows (per its own support matrix). This fork's head looks like upstream merges; UWP-specific changes weren't isolable in review. ANGLE's real Dev Mode role today is mostly *inside* SDL's GLES2 path. If you need GLES3.1+ features, ANGLE-on-D3D11 is incomplete by upstream's own table.

### B.5 Samples, research & community (20–22, 30–32)

- **20. XboxSeries** — One researcher's Series S Dev Mode internals report (no code, **no license**). Fascinating ERA/SRA/hypervisor context; single-device, single-OS-build, AI-formatted claims. Read as hypotheses, never as API documentation. Nothing here is needed to write a UWP game, and systems-internals probing is out of scope for a porting plan.
- **21. uwp_gl_sample** — "Barebones OpenGL on UWP" (SDL + Mesa Gallium + glad). **Your best first build.** Small VS solution, claims Series execution. Start here before BurgerDoom.
- **22. devmodewiki** — Active Docusaurus wiki (xbox-setup/development/emulation/ports). Good for setup flow cross-checks; still community-edited — verify limits against MS pages.
- **30. XBDev "HelpfullLinksDev"** — Link farm (aerisarn/worleydl libs, Godot-UWP Reddit guides, Unity-UWP builder). Useful archaeology; dates to 2025-05, expect rot. Note Godot UWP export is Godot **3.x-era** documentation — Godot 4 has no official UWP export in reviewed sources.
- **31. ConsoleMods list** — Catalog of Dev Mode UWP apps/emulators/games (RetroArch, Dolphin/XBSX2/Xenia forks, source ports like DevilutionX/OpenLara). Value: proves breadth of what *has* been made to run; emphasizes how much is "outdated." No build guidance.
- **32. Emulation Revival** — Polished consumer hub linking the same ecosystem (identifies e.g. Melee-UWP ports). Value: discovery + tester reports; zero engineering depth. Never cite it for API claims.

---

## C. Repository case-study comparison

### C.1 Grouping by *actual* approach (verified from code/docs, not names)

| Group | Repos | Core trick | Why it exists |
|---|---|---|---|
| **Hand-written D3D12 backends** | KytyPS5, Jadyx | Reuse upstream SPIR-V/shader-recompiler; translate SPIR-V→DXIL (`spirv_to_dxil` + `dxil.dll` signing); write D3D12 pipelines/heaps/caches by hand | Guest GPUs (PS5/Switch) already compile to SPIR-V in upstream; Vulkan can't run natively in UWP |
| **Vulkan→Dozen→D3D12** | gow3_xbox, WWHD-UWP (+ Mesa forks beneath) | Keep upstream Vulkan renderer untouched; ship Mesa Dozen ICD in the package | Avoids renderer rewrite; pays translation + driver-maturity tax |
| **OpenGL/GLES→(Mesa Gallium / ANGLE)→D3D11/12** | 2ship (GL default), uwp_gl_sample, SDL GLES2, switch-gdx | Keep GL renderer; translate at the GL layer | Old/decomp codebases are GL-native and undemanding |
| **D3D11 native** | 2ship (alt backend), DirectXTK-based code, SDL_Renderer | Write/port to D3D11 FL10.1/11.0 | Simplest native API in UWP; driver handles memory/sync |
| **Guest-code execution** (orthogonal!) | gow3/Kyty (PS4/PS5 x86-64), Jadyx (ARM64→x64 Dynarmic JIT), WWHD/Melee (static recompilation), decomp ports (native C/C++ rebuild) | *How guest CPU code runs*: direct native execution with *FromApp W^X flips, JIT, or ahead-of-time recompiled/decompiled C++ | This — not graphics — is usually the hardest, most legally-sensitive layer |
| **Platform glue** | SDL3-uwp, libuwp, xbox-swap, dawn-uwp | Windowing/CoreWindow, XInput/Windows.Gaming.Input, XAudio2/WASAPI, file pickers/USB, commit-cap pagers | Every port above re-assembles some subset of this |

### C.2 Architecture comparison (evidence-based)

| Aspect | KytyPS5 | Jadyx | gow3_xbox | WWHD-UWP | BurgerDoom / 2ship |
|---|---|---|---|---|---|
| Upstream seam | Shared renderer logic split from Vulkan calls; D3D12 beside Vulkan [Verified: XBOX_CHANGES] | Eden Vulkan backend as *model* for own D3D12 backend | SpartanPort/shadPS4 Vulkan kept; Dozen below | Overlay on pinned upstream commit; GX2→Vulkan upstream, Dozen below | Game logic untouched; SDL/platform shim only |
| Build | CMake `KYTY_BUILD_UWP`, own `src/uwp` + `uwp.ps1` packaging/deploy | CMake `uwp-x64` preset, Ninja + `vcvarsall x64 uwp` (Store CRT), source-built OpenSSL | clang-cl + Store CRT + WindowsApp.lib; GH Actions builds Dozen→launcher→zip | Needs external depot/tooling; on-console Clang/Python stages | CMake `PLATFORM_UWP`, bundled SDL2-UWP |
| Windowing/UI | WinUI 2 launcher + overlay | Custom frontend (Home/Library/Settings), ImGui-era Eden bits headless-off | CoreApplication host + ImGui menu | Custom menu (Manrope font), ImGui | SDL window; lib menus |
| Input | 4× Xbox pads → DualSense incl. headset mic/speaker (WASAPI), impulse triggers | Xbox pads→ Switch pro/Joy-Con emulation, strict disconnect handling | SDL3; guest pad APIs were milestone-gated in dev log | SDL3-UWP controllers | SDL gamepad |
| Audio | XAudio2 (+ headset WASAPI capture) | XAudio2 2.9 | Via upstream/FFmpeg decoders; milestone-gated | SDL3-UWP audio | SDL_mixer-era / SDL audio |
| Storage | USB via *FromApp file APIs, `.zar`, LocalState caches | USB/folder/zip import, portal upload, internal DLC store | USB `\dumps\…` or `D:\DevelopmentFiles` (≤3 deep auto-find) | USB-only prepared files reused across launches | LocalState / `D:\` `E:\` choices (2ship) |
| Memory strategy | 64 KiB commit-on-touch guest memory (can't reserve 13.8 GiB); swap file; texture downgrade options | Memory guard shrinks caches near 5120 MiB; ASTC→BC3 transcode; documents unfixable "memory wall" title | Pager borrowed from Kyty lineage; 720p default *because* 4K spills ~450 MiB to disk | ≥3 GiB free USB for prepared output | Not needed (small footprints) |
| Shaders | Pipeline cache stores *translated shaders only* (prebuilt PSOs OOM'd); SM6.4 limits, skips tessellation | SPIR-V→DXIL + disk cache; first-compile stutter acknowledged; FL11.0/SM6.4/no Agility | Precompile step (7k shaders ≈ 3 min) or compile-on-draw with late pop-in | Latte translation upstream (Cemu-derived) | Fixed-function/simple GLSL — negligible |
| Packaging | APPX via Device Portal, set type=Game in Dev Home | Signed `.appx`+`.cer`+SHA256, in-app updater | Self-signed test cert in-repo (by design, vouches for nobody) for upgrade-in-place | APPX via Device Portal, type=Game | APPX/MSIX bundle |

### C.3 Reusable patterns (steal these) vs. study-only (don't copy blindly)

**Reusable patterns:**
1. **One-commit-per-topic Xbox delta + changes table** (KytyPS5) — keeps upstream rebases survivable.
2. **Pinned-upstream overlay** (WWHD/Melee) — honest about divergence; pair with a `STATUS.md`.
3. **Documented build env that *verifies itself*** (Jadyx `build-env.bat`: vswhere-on-PATH, Store CRT check) — UWP builds fail silently into desktop mode otherwise.
4. **Shader/pipeline disk caches + "precompile vs hitch" UX choice** (gow3/Jadyx/Kyty).
5. **Memory ledger + cache shrink near commit cap; resolution as a memory knob** (Jadyx guard; gow3 720p default).
6. **Thin platform shim** (libuwp/SDL) isolating CoreWindow, pickers, paths (`LocalState`, removable storage), lifecycle (`uwp_ProcessEvents`).

**Study-only / high-risk to reuse:**
- Guest-memory pagers & xbox-swap (correct only within their allocator invariants; GPL-3.0 on xbox-swap infects copy-paste).
- mesa_ai_slop_version commits (unreviewed compiler lowerings — may miscompile silently).
- BurgerDoom's broad capabilities (`runFullTrust`, `broadFileSystemAccess`) — request minimum capabilities; full-trust changes your sandbox story and reviewability.
- Any decomp/recomp guest code or patch XMLs — legally and technically inseparable from the original game.
- Dawn-UWP / ANGLE-fork heads — completeness unproven; depend on them only behind an abstraction you can swap.

### C.4 Why one port's success proves nothing about another game

Each case study succeeds by exploiting *its* upstream's structure: Kyty/Jadyx had SPIR-V-emitting shader recompilers; gow3 runs guest x86-64 natively because PS4→Xbox is same-ISA (an ARM or PowerPC guest would need a JIT/recompiler); decomp ports had years of reverse-engineered C++ handed to them. Your future game brings its own matrix: different ISA concerns (none, if it's your x64 source), different API (your GL/Vulkan/D3D11 renderer may map better to Mesa/Dozen/D3D11 than to a heroic D3D12 rewrite), different middleware (a single Win32-only plugin can veto UWP), different memory profile (5 GB unified cap). **Transfer the *checklist*, not the conclusion.**

---

## D. Compatibility matrix and missing information

Target fixed: **Series X|S · Dev Mode · UWP x64 · personal use.** ✅ documented/working in reviewed sources · ⚠️ possible with major caveats · ❌ not in this workflow · ❔ unverified.

| Your stack ↓ | Verdict | Nearest documented alternative |
|---|---|---|
| **C/C++ + SDL2/3 (2D or GL/GLES renderer)** | ✅ Best-supported hobby path (#21,#15,#23,#25) | — |
| **C++ + Direct3D 11** | ✅ Native UWP API (+ DirectXTK #7) | — |
| **C++ + Direct3D 12 (hand-written)** | ✅ API exists (FL11.0) but highest effort; cap features at FL11.0/SM6.x-era, no Agility/mesh-shader assumptions [Claimed by #8,#14 measurements] | Use DirectXTK12/D3D12MA helpers; or drop to D3D11 |
| **C++ + OpenGL (desktop GL)** | ⚠️ Via Mesa Gallium-on-D3D12 (#25,#21) or GLES via ANGLE (#28); expect extension/version gaps, test every shader | Port hot paths to D3D11 |
| **C++ + Vulkan** | ⚠️ No native Vulkan in UWP; Dozen (#11/#25) translates to D3D12 — works in #9/#13, driver maturity is your risk | Rewrite backend on D3D12 (#8/#14 pattern) only if Dozen profiling condemns it |
| **C++ + WebGPU** | ❔ Dawn-UWP (#24) early | SDL+D3D11 today |
| **C# + Unity (UWP export)** | ⚠️ Legacy Unity UWP flow (version-sensitive; community guides #30) — *not* the GDK page #4. IL2CPP/`.NET` scripting backend & plugin (WinRT-partition) limits apply | Unity GDK = commercial route; or MonoGame/UWP C# for small games (outside reviewed set — verify current support) |
| **C# without engine (UWP/WinRT, SharpDX-era)** | ⚠️ Historically viable; current library maintenance unverified in this set | C++ shim + C# game logic via WinRT components (complexity ↑) |
| **Java/Kotlin + LibGDX** | ⚠️ switch-gdx transpilation (#18), GLES2-class | Rewrite in C++/SDL if you need GL3/networking |
| **Rust** | ❔ No official UWP-Xbox Rust toolchain in reviewed sources; `windows` crate + AppContainer experiments would be R&D, plus C++ shim for SDL/D3D | Prototype logic in Rust on PC; ship C++ UWP shell — only if team strength justifies FFI |
| **Godot** | ⚠️ 3.x UWP export docs (#30); **Godot 4: no official UWP export found** | Godot GDK (commercial, mentioned on MS hub) or pin Godot 3.x knowingly |
| **Unreal** | ❌ No UWP Dev Mode path in reviewed sources (GDK commercial only) | Commercial ID@Xbox route |
| **Defold** | ❌ Publicly: approved-dev GDK only (#5) | Commercial route |
| **Anything Win32-only** (HWND assumptions, desktop-only DLLs, x86, drivers, anti-cheat) | ❌ Until each dependency has a WindowsStore-partition build | Replace/shim deps one-by-one; re-audit |
| **Binary-only game** | ❌ (see A.4) | Streaming client or reimplementation |

**Cross-cutting UWP constraints to check for *any* stack:** *FromApp memory/file APIs & W^X (no RWX pages — JITs must flip RX↔RW), AppContainer file visibility (install dir read-only; use LocalState/removable with capabilities), single-file-size and path quirks reported by the community (verify on device; design streaming/chunking early), controller-first UI (10-foot, no mouse assumptions), suspend/terminate lifecycle, no background execution for games.

**Missing info that would change the recommendation** — collect before estimating: repo URL/license file · build system & exact compiler/SDK versions that build it *today on PC* · renderer API + shader language/count · every binary dependency · peak PC memory (commit, incl. GPU) · largest single files/streaming pattern · input/audio/netcode stack · target: Series S as min-spec? Bring these and Section D collapses to one row.
