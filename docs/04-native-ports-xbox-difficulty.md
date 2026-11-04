# 04 — Every Native PC Port (ports.matheusbrauna.com.br) Rated for Xbox Dev Mode

**Catalog snapshot:** 2026-11-04 · Site header: **304 ports across 253 games** (Playable 53 · In-game 104 · Intro 3 · In-progress 13 · Not stated 131 ports; Static recompilation 260 · Native execution 44). Consoles: Xbox 360 (110 ports), PlayStation 4 (39), Xbox (33), Nintendo 64 (29), PS2/PS3/Switch (18 each), PS1 (12), PSP (10), GameCube (7), Wii (5), Dreamcast (3), 32X (1), NAOMI 2 (1).

**What is being rated:** the *incremental* difficulty of taking the PC port listed on the site (assuming it builds on your PC and you supply your own legally obtained copy of the game) to **Xbox Series X|S Developer Mode (UWP x64, FL11.0 D3D11/D3D12, 5 GB unified cap as "Game", AppContainer)** — *not* the difficulty of creating the PC port. Ratings are **[Inference]** from verified toolchain/renderer/status data, except D1 rows which cite a tested Xbox recipe/fork. **I did not build any of these 304 ports.** The site itself states it "does not test builds" and statuses repeat each README — so a "Playable" label is a claim, not a measurement [Verified: /about/].

**How to read a row:** `Best starting port` = the catalog entry I'd start from on PC (Windows + D3D preferred for Xbox). For multi-port games the *easiest-for-Xbox* port is chosen, which is often not the most popular one.

## Rating scale

| Code | Meaning | Typical effort (experienced dev, part-time in brackets) |
|---|---|---|
| **D1** | **Already proven on Xbox** — tested recipe or maintained UWP fork exists | Days–2 weeks, following docs |
| **D2** | **Moderate** — same *proven family* (runtime already on Xbox), PC port Playable/Not-stated, Windows D3D/RT64 build | 2–6 weeks (1–3 months) |
| **D3** | **Hard** — proven family but a blocker: Vulkan/OpenGL-only (Dozen/Mesa or presenter rewrite), In-game PC status, no Windows build, motion/peripheral remapping | 1–3 months (3–6 months) |
| **D4** | **Very Hard** — *toolchain runtime itself* not yet on Xbox (you port the runtime first, then the game), or small PS4 native-execution title | 3–9 months |
| **D5** | **Extreme** — runtime unproven **and** heavy game (open world/streaming, SPU/Cell, PS4 AAA memory, Switch NVN) or PC port barely In-game/Intro | 9+ months, possibly a team |
| **BX** | **Blocked as listed** — repo gone, or 32-bit native-execution binary (UWP Xbox is x64-only) | Recover source / change approach first |

Modifiers applied per game (each ≈ ±1 tier): **+** harder: Vulkan-only (needs Mesa Dozen layer, though proven), OpenGL-only (Mesa Gallium or D3D11 presenter rewrite), Linux/macOS/Android-only (port the PC port to Windows first), In-progress/Intro, Kinect/guitar/portal peripherals (UWP only sees Xbox-compatible controllers; custom USB is effectively unavailable), online dependences, DLSS (impossible on AMD Xbox — must fall back to FSR/native), huge install/streaming vs 5 GB cap and AppContainer file rules. **−** easier: D3D11 (driver-managed, FL11.0-safe), existing SDL2/3 host, small/2D/fighting-game footprint, split-screen local play (Xbox-native use case).

> **D3D12-on-Demo Mode zinger [Verified from jajdp/rush2-xbox]:** `ID3D12PipelineState::GetCachedBlob()` and `ID3D12Device1::CreatePipelineLibrary()` **remove the device** on Xbox in Developer Mode. Any "D3D12 = easy" assumption must survive a PSO-cache audit. D3D11 ports dodge this entirely.

## Toolchain families — the real unit of difficulty

Games don't port one-by-one; *runtimes* do. Port a runtime once and its whole family drops a tier.

| Family (catalog share) | Xbox status [Verified via GitHub API 2026-11-04] | Route to console |
|---|---|---|
| **N64Recomp + RT64/plume** (29) | ✅ **Proven.** worleydl forks: `rt64-dev` (uwp-dk64), `N64ModernRuntime-dev` (uwp-rebase), `RecompFrontend-dev` (uwp-compat), `plume-uwp`, `uwp-dep` (rt64 branch); jajdp's Rush 2 plays at 59 fps on Series X (launch 5 min→20 s after shader fix). Traps: Ninja+clang-cl (VS generator MSB8020), `SDL_INIT_HAPTIC` absent in WinRT SDL, `SDL_HINT_JOYSTICK_WGI`, LocalState paths, invalid `stderr` | D3D12 via plume-UWP; disable PSO-caching APIs above |
| **PSXRecomp / PS1 generic + RecompOne** (12) | ✅ **Proven.** Bloody Roar II plays on Series X since 2026-10-19 (13 guarded patches, inert OpenGL backend → **software rasteriser**, OpenBIOS). RecompOne proven via a .NET NativeAOT recipe (Castlevania Chronicles, outside catalog) | Software/D3D11 presenter; CPU rendering = Series S risk |
| **WiiCompiled + Aurora** (in 2/5 Wii) | ✅ **Proven for Mario Kart Wii**: 58 fps, Aurora patches (GX via Dawn/WebGPU→D3D12, SDL3, CoreWindow surface), 12 runtime changes *described* (Wiicompiled has no license → recipe-only) | Dawn-UWP + SDL3-UWP |
| **Yakumo-style PSP recomp** (1/10 PSP) | ✅ **Proven for Monster Hunter Portable 3rd HD**: Vulkan-only → **Mesa Dozen** (repo carries a 45 KB Dozen triangle test — copy that method), FFmpeg-UWP for music/movies, GameCube-style ISO chunking tools | Dozen first, game second |
| **XenonRecomp / hedge-dev line** (~15 X360) | ✅/⚠️ **One game proven**: `worleydl/UnleashedRecomp-uwp` (uwp-port branch, 2025-04, "disable game-breaking options", manual externals). Other Xenon games share the recompiler but *not* one runtime — each game is its own host port | Per-game D3D12/D3D11 host adaptation |
| **ReXGlue (Xenia-rooted)** (~90 X360 — the giant) | ⚠️ **Early/buggy**: `worleydl/rexglue-sdk-dev` branches `uwp-compat` (8 commits: "early buggy rendering", SDL/libuwp linkage, swapchain; diverged, 16 behind) + `uwp-xaudio`. No ReXGlue game was found playable on Xbox in this research | **Port this runtime = unlock ~99 X360 games.** Every ReXGlue row below is D4\* = "D4 today, ≈D3 after runtime lands" |
| **Original-Xbox recompilers** (33) | ❌ No Xbox-UWP runtime precedent found (GitHub search 2026-11-04). x86 guest helps CPU translation; D3D8-lift + 32-bit-isms hurt | D3D11 xboxrecomp ports are the beachhead |
| **PS4 native execution / bbport** (39) | ⚠️ Pattern proven by *non-catalog* siblings from my earlier research: `Cosmo/gow3_xbox` (alpha, Dozen, 720p-for-memory), KytyPS5 D3D12 pager. x86-64 guest runs directly, but `Virtual*FromApp` W^X, lazy-commit guest memory and the 5 GB cap vs PS4's ~5.5 GB game budget dominate | Dozen (fast) or D3D12 rewrite (months); shader precompile UX mandatory |
| **PS2Recomp** (18) | ❌ No Xbox precedent. EE/VU/IOP + custom GS (often OpenGL) runtimes are young; most ports In-game. **Reality check:** the XBSX2 emulator already runs PS2 discs on Dev Mode — a recomp port must justify itself (perf/mods) vs that | OpenGL→Mesa or GS rewrite; consider emulator instead |
| **ps3recomp** (18) | ❌ No Xbox precedent. Cell PPU+SPU recompilation is the hardest CPU problem in the catalog; catalog entries typically "first level", one cites ~13 fps on PC | Not a beginner/intermediate target at all |
| **DolRecomp / gcn-recomp** (7) | ❌ No direct precedent; Aurora (GX layer) *is* Xbox-proven via Wii route, GXRuntime is not | Aurora-style Dawn route is the hope |
| **Switch recompilers** (18) | ❌ No Xbox precedent; AArch64→x64 + NVN→Vulkan→Dozen triple translation, 4–16 GB titles vs 5 GB cap. Jadyx emulator (prior research) already plays Switch games on Series — recomp ports compete with that | Don't, unless researching recompilers |
| **Dreamcast/NAOMI/32X recompilers** (5) | ❌ No precedent; tiny footprints help | 32X 2D is the only gentle one |

**Series S warning (applies to every D1 recipe):** jajdp's tested recipes state *Series X only, Series S never tried* — weaker GPU + tighter memory. Treat S as +½ tier of perf risk everywhere.

## Already on Xbox (D1) — start here

| Game | Evidence |
|---|---|
| **Bloody Roar II (PS1)** | jajdp/bloody-roar-2-xbox: plays, 16:9, controller, FPS toggle; software rasteriser |
| **Mario Kart Wii (Wii)** | jajdp/retro-rewind-xbox: 58 fps incl. Retro Rewind mod distro |
| **Monster Hunter Portable 3rd HD (PSP)** | jajdp/mhp3rd-xbox: plays with music/movies via Dozen + FFmpeg-UWP |
| **Majora's Mask (N64)** | worleydl/Zelda64Recomp-uwp fork (uwp-compat-1.2.2) — verify current build state yourself; release asset is notes |
| **Mystical Ninja Starring Goemon (N64)** | worleydl/Goemon64Recomp-uwp fork — same verify-yourself caveat |
| **Sonic Unleashed (X360)** | worleydl/UnleashedRecomp-uwp (2025) + community UWP listings from earlier research — expect manual externals fetch and disabled options |
| **God of War III Remastered (PS4)** | Catalog lists the PC parent (`FelipePrado0/gow3_pc` lineage); the Xbox fork `Cosmo/gow3_xbox` from my previous audit is alpha-playable on Series X\|S (720p default for memory, shader precompile step) |

---

# Complete list — every game (253)

## Xbox 360 — 99 games / 110 ports (mostly ReXGlue)

> `D4*` = D4 today solely because the ReXGlue UWP runtime is early; ≈D3 once it matures. Many X360 titles also exist as Microsoft back-compat or native Series releases — check before investing (a Dev Mode port only wins for mods/uncapped fps/learning).

| Game | Best starting port (toolchain · renderer · PC status) | Xbox diff. | Why |
|---|---|---|---|
| 'Splosion Man | ReXGlue · Vulkan · Playable | D4*→3 | Small XBLA platformer; Vulkan adds Dozen until ReXGlue D3D12-UWP works |
| 007 Legends | ReXGlue (007 multi-game repo) · D3D12 · In progress | D5 | PC side "under investigation" — port the PC port first |
| 2010 FIFA World Cup | ReXGlue · — · Not stated | D4* | Standard ReXGlue sports title |
| 2014 FIFA World Cup Brazil | ReXGlue · D3D12 · Not stated | D4* | Launcher/dump-verify must become controller-first |
| 3 on 3 NHL Arcade | ReXGlue · D3D12 · Not stated | D4*→3 | Tiny XBLA, full matches reported |
| Aegis Wing | ReXGlue · DX12 · Not stated | D4*→3 | Tiny shmup; LAN co-op is the only extra |
| Army of Two (×2) | ReXGlue · D3D12 · **Playable** (OpenPortroid) | D4* | Co-op netcode w/o EA servers won't transfer 1:1; split-screen will |
| Asura's Wrath | ReXGlue · — · In progress | D5 | QTE-video heavy; PC port unfinished |
| Bakugan Battle Brawlers | ReXGlue · Linux-only · In-game | D5 | No Windows build yet |
| Banjo-Kazooie: Nuts & Bolts | ReXGlue · custom D3D12 · In-game | D5 | Vehicle physics + large worlds, In-game only |
| Big Bumpin' | ReXGlue (BK collection) · D3D12/Vulkan · Not stated | D4*→3 | Promo mini-game, tiny footprint |
| Borderlands | ReXGlue · — · In-game (0★) | D5 | Earliest-stage, co-op shooter scope |
| Burnout Revenge | XenonRecomp · **macOS-only** Metal · Not stated | D5 | No Windows build — double port |
| Call of Duty 3 (×3) | XenonRecomp · **D3D11** · In-game (all 15 levels load) | **D3** | Pick the D3D11 port over 2× ReXGlue — best X360 FPS beachhead |
| Call of Duty: Black Ops II | ReXGlue · Vulkan · Not stated | D5 | Campaign+MP+Zombies scope; netcode |
| Call of Duty: Modern Warfare 2 | Static recomp · Vulkan · Not stated | D4 | Non-ReXGlue runtime to bring over; Steam/LAN MP won't map (no Steam in UWP) |
| Civilization Revolution | ReXGlue · — · Not stated | D4* | Turn-based = forgiving perf; Lua mods need sandbox audit |
| Condemned 2: Bloodshot | ReXGlue · Win/Linux · In-game | D4* | Standard hard-ReXGlue |
| Crackdown | ReXGlue · D3D12/Vulkan · Not stated | D5 | Open-world streaming vs 5 GB |
| Crystal Defenders | XenonRecomp · **D3D11**/OpenGL · **Playable** | **D3** | Tower-defense, tiny — easiest X360 after Unleashed |
| Dead Rising 2: Case West | XenonRecomp · Vulkan · Playable | D4 | Dozen route; zombie crowds test CPU |
| Dead Rising 2: Case Zero | XenonRecomp · Vulkan · Playable (completed end-to-end) | D4 | As above, smaller |
| Deadly Premonition | ReXGlue · D3D12 · Not stated | D4* | Open-world-ish but low-fi rendering forgives |
| Dragon Age: Origins | DAORecomp · **Android-only** Vulkan · In-game | D5 | ARM/Android host; huge RPG saves/data |
| Dragon Ball Z: Burst Limit | ReXGlue · D3D12 · Not stated | D4*→3 | Arena fighter = ideal ReXGlue shape; DLSS must be dropped for FSR/native |
| Enchanted Arms | ReXGlue · Win/Linux · In-game | D4* | JRPG, modest rendering |
| F.E.A.R. | ReXGlue · Linux/Deck-first · Not stated | D5 | Windows support "planned", not present |
| F.E.A.R. Files | (same repo as F.E.A.R.) | D5 | Explicitly future work even on PC |
| Fable II | ReXGlue · **Android-only** Vulkan · In-game | D5 | No Windows host; large RPG |
| FIFA Street (2012) | ReXGlue · D3D12/Vulkan · Not stated (482★) | D4* | Popular; custom online won't transfer directly |
| Forza Horizon (×3) | ReXGlue · Vulkan/D3D12 · In-game/Not stated | D5 | Open-world racer streaming + DLC + online free-roam scope |
| Forza Motorsport 4 | ReXGlue · — · In progress | D5 | "Experimental source release" |
| Fuse | ReXGlue · — · Playable | D4* | 4P split-screen suits Xbox; shooter size |
| Gears of War 2 | ReXGlue · DX12/Vulkan · In-game (Act 1) | D5 | UE3 streaming, Act-1-only PC state |
| Gears of War 3 (×2) | XenonRecomp · D3D12 · **Playable** (vs ReXGlue In-game) | D4 | Start from Xenon port; UE3 + LAN/online scope keeps it D4 |
| Geometry Wars: Retro Evolved 2 | ReXGlue · D3D12/Vulkan · Not stated | D4*→3 | 2D twin-stick — perfect first ReXGlue-UWP test case |
| Ghost Recon Future Soldier | ReXGlue · **macOS-only** · In-game | D5 | No Windows build |
| GoldenEye 007 (XBLA remaster) | ReXGlue · D3D12/Vulkan · Not stated | D4*→3 | Small levels; LAN MP audit needed |
| GoldenEye 007: Reloaded | ReXGlue · — · In-game (2 missions) | D5 | PC port early |
| Guitar Hero II | ReXGlue · Linux/Deck Vulkan · Not stated | D5 | **Instrument controllers**: UWP sees Xbox-compatible pads only — guitar support is the project |
| Guitar Hero: Metallica | ReXGlue · Vulkan · In-game | D5 | Same peripheral wall |
| Halo Mega Bloks | ReXGlue · Vulkan · In-game | D4* | Unreleased prototype — small but rough |
| Hard Corps: Uprising | ReXGlue · DX12/Vulkan · Not stated | D4*→3 | 2.5D XBLA run-and-gun |
| Hydro Thunder Hurricane (×2) | ReXGlue · Vulkan option · Not stated | D4*→3 | Arcade racer, modest size |
| James Bond 007: Blood Stone | ReXGlue (007 repo) · D3D12 · In progress | D5 | "Under investigation" on PC |
| Juiced 2: Hot Import Nights | ReXGlue · D3D12 · In-game | D4* | Career-deep but gfx/perf issues remain on PC |
| Kameo: Elements of Power | ReXGlue · Vulkan · In-game | D4* | Launch-title scope |
| Lost Odyssey | ReXGlue · D3D12/Vulkan · Playable (**archived**) | D4* | 4-disc JRPG data handling in AppContainer is the work; archived upstream |
| Madden NFL 08 | ReXGlue · D3D12 · In-game | D4* | Sports-standard |
| Marvel Ultimate Alliance | ReXGlue bundle · D3D12/Vulkan · Not stated | D4* | 4P local co-op suits console |
| Marvel Ultimate Alliance 2 | (same bundle) | D4* | — |
| Marvel Ultimate Alliance Gold | (same bundle) | D4* | — |
| Midnight Club: LA Complete (×2) | ReXGlue · DX12/Vulkan · Not stated (Android port = Intro, archived) | D5 | Open-world streaming racer |
| Naruto UNS Generations | XenonRecomp · Vulkan Android/Win · Not stated | D4 | Arena fighter via Dozen |
| Naruto × Boruto Connections | XenonRecomp · **Android-only**, is an X360 *mod* · Not stated | D5 | Mod-of-a-game provenance + no Windows host |
| Naruto: Rise of a Ninja | XenonRecomp · Vulkan · Not stated | D4 | Dozen route |
| NCAA Football 14 | ReXGlue · D3D12/Vulkan · Not stated | D4* | Mod-installer launcher must be redesigned for sandbox |
| Need for Speed: Carbon | XenonRecomp · Vulkan multi-OS · Not stated | D4 | Open-world-lite; Dozen |
| Need for Speed: Most Wanted '05 | Static recomp · Vulkan, no Windows listed · Not stated | D4 | Windows host work first (Deck/Linux/Mac focus) |
| NFL Head Coach 09 | XenonRecomp · D3D12 · In-game | D4→3 | Menu/sim-heavy = GPU-easy; D3D12 native helps |
| NHL 14 | ReXGlue · custom Vulkan · **Playable** (full offline) | D4* | Vulkan-only renderer |
| NHL 2K8 | ReXGlue · D3D12 · Not stated | D4* | — |
| NHL Legacy Edition | ReXGlue · D3D12/Vulkan · Not stated | D4* | Roster-mod packaging in sandbox |
| Perfect Dark (2010) (×2) | ReXGlue · D3D12/Vulkan · Not stated | D4*→3 | XBLA remaster, split-screen — strong candidate once runtime lands |
| Perfect Dark Zero | ReXGlue · — · **Playable** | D4* | Full playability claimed on PC |
| Pirates of the Caribbean: AWE | ReXGlue · Vulkan · In-game | D4* | DLAA feature must be cut/replaced |
| Plants vs. Zombies | ReXGlue · — · **Playable** | D4*→3 | 2D — another ideal runtime smoke-test (mouse→pad already console-native design) |
| PocketBike Racer | ReXGlue (BK collection) · Not stated | D4*→3 | Promo mini |
| Pro Evolution Soccer 6 | ReXGlue · D3D12/Vulkan · Not stated | D4* | — |
| Project Gotham Racing 4 | ReXGlue · — · Not stated (known crash) | D5 | Arcade-cabinet crash = PC port immature |
| Quantum of Solace | ReXGlue (007 repo) · D3D12 · In-game | D4* | The one actually in-game from that repo |
| Rayman 3 HD | ReXGlue · D3D12 · **Playable** | D4*→3 | 3D platformer, modest size |
| Resident Evil CODE:Veronica | ReXGlue · — · In-game | D4* | Fixed-camera = perf-forgiving |
| Rumble Roses XX | XenonRecomp · — · In-game | D4 | Small arena scope after host work |
| Saints Row | ReXGlue · D3D12 · In-game (on-foot exploring) | D5 | Open world, PC state early |
| Silent Hill: Downpour | ReXGlue · D3D12 · **Playable** | D4* | UE3 but contained environments |
| Skate | ReXGlue · Vulkan/D3D12 · In-game | D5 | Open-world + dual-stick flick system fine on pad, streaming isn't |
| Skate 2 | ReXGlue · D3D12 · (player package) | D5 | Same |
| Skate 3 (×2) | ReXGlue · DX12/Vulkan · Not stated (+ Android Playable spin-off) | D5 | Open world; SteamVR feature is dead weight on Xbox |
| Skylanders: Imaginators | ReXGlue · D3D12 · In-game | D4* | **Virtual Portal in port saves you** — real USB portal won't work in UWP |
| Skylanders: Spyro's Adventure | ReXGlue · D3D12 · In-game | D4* | Portal emulation built-in |
| Skylanders: Swap Force | ReXGlue · D3D12 · In-game | D4* | Virtual portal yes; "real USB portal" feature no |
| Sneak King (X360) | ReXGlue (BK collection) · Not stated | D4*→3 | Promo mini (OG-Xbox version below may be easier) |
| Snoopy Flying Ace | ReXGlue · — · Not stated | D4* | Epic Online Services MP will not run in UWP sandbox — local only |
| Sonic Free Riders | XenonRecomp · D3D12/Vulkan · In-game | D4 | **Kinect game**, but port already emulates controls → pad play possible; no Series Kinect exists |
| Sonic Unleashed | XenonRecomp (hedge-dev) · 5,333★ | **D1** | UWP fork exists (see D1 table); still the biggest "easy" here — verify build |
| Spider-Man: Edge of Time | ReXGlue · D3D12/Vulkan · Not stated | D4* | "DLSS 5" claim must be stripped on AMD |
| Stuntman: Ignition | ReXGlue · D3D12 · In-game | D4* | Level-based driving |
| Super Street Fighter II Turbo HD | ReXGlue · D3D12/Vulkan · Not stated | D4*→3 | 2D fighter, tiny |
| Superman Returns | ReXGlue · D3D12/Vulkan · In-game (early) | D5 | Open-city scope, early PC state |
| Tekken Tag Tournament 2 | XenonRecomp · **repository gone** | **BX** | Nothing to build from until source reappears |
| Tenchu Z | ReXGlue · D3D12/Vulkan · In-game | D4* | System-Link co-op → LAN audit |
| The Darkness | ReXGlue · D3D12 · Not stated | D4* | Linear FPS scope |
| Tony Hawk's Project 8 (X360) | ReXGlue · Linux-tested · Not stated | D5 | Windows untested per listing |
| Vigilante 8 Arcade | ReXGlue · D3D12 · In-game | D4*→3 | Small arena car-combat |
| WET | ReXGlue · — · **Playable** | D4* | Linear action |
| WWE 2K14 | ReXGlue · Vulkan · In-game | D4* | DLC/mod sandbox handling |
| WWE All Stars | ReXGlue · Vulkan · **Playable** | D4* | Online Player Match won't transfer; local 4P will |
| WWE SmackDown vs. Raw 2011 (×2) | ReXGlue · D3D12/Vulkan · In-game/Not stated | D4* | Exhibition smooth, story untested (per listing) |

## Original Xbox — 26 games / 33 ports

x86 guest ⇒ CPU translation is the easy half; the D3D8-era GPU lift, 32-bit host assumptions, and zero UWP runtime precedent are the hard half. Back-compat check applies doubly here.

| Game | Best starting port | Xbox diff. | Why |
|---|---|---|---|
| 007: From Russia with Love | XBE Recomp · D3D12 · Not stated | D4 | Runtime-first (XBERecomp family unproven on UWP) |
| 007: Nightfire | XBE Recomp · D3D12 · Not stated | D4 | — |
| Black | XBE Recomp · D3D12 · Not stated (870★) | D4 | Popular; same runtime gate |
| Blood Wake | xboxrecomp · **D3D11** · **Playable** | **D3** | D3D11+Playable+split-screen = best OG beachhead |
| Buffy the Vampire Slayer | XboxXBERecomp · macOS Vulkan · In-game | D5 | No Windows build |
| Colin McRae Rally 2005 | XBE Recomp · D3D12 · Not stated | D4 | — |
| Conker: Live & Reloaded (×4) | xboxrecomp · GL/Vulkan · **Playable** (rashevskyv) | D3 | Choose Playable port; GL→Mesa/D3D presenter; room-code online in another fork won't transfer directly |
| Darkwatch | XboxXBERecomp · D3D12 · In-game, **archived** | D4 | Split-screen co-op bonus; archived host |
| Dead or Alive 2 Ultimate (×2) | xboxrecomp · **D3D11** · In-game | D3 | Arena fighter; Insignia online in one fork = no-go in sandbox, local play fine |
| Dead or Alive 3 (×3) | xboxrecomp · **D3D11** · **Playable** | **D3** | Best OG fighter candidate (ignore the Android GLES port) |
| Dead or Alive Xtreme BV | Static recomp hand runtime · **D3D11** · **Playable** | D3 | "Aiming to become readable source" helps porting |
| Def Jam: Fight for NY | Static recomp · D3D11/Vulkan · Not stated ("mature, 60 fps") | D3 | Strong PC state claimed |
| Halo: Combat Evolved | Static recomp · iOS/macOS Metal/ANGLE · Playable | D4 | No Windows host; also natively on Series via MCC — learning value only |
| Jet Set Radio Future | xboxrecomp · macOS Metal/D3D-lift · In-game | D4 | Windows host missing; beloved but double-port |
| Midnight Club 3: DUB Remix | XboxXBE-Recomp · **Android-only** Vulkan · In-game | D5 | No Windows build; open-world |
| Midtown Madness 3 | xboxrecomp · **D3D11** · Not stated | D3 | System-Link → LAN audit |
| Ninja Gaiden Black (×2) | xboxrecomp · Vulkan multi-OS · Not stated (vs native-exec GL Playable) | D4 | Native-exec OG-x86 binary path can't be 32-bit in UWP — use recomp+Vulkan/Dozen |
| Predator: Concrete Jungle | xboxrecomp · OpenGL · Not stated | D4 | GL→Mesa presenter work |
| Sneak King (Xbox) | xboxrecomp · D3D11/multi-GL · **Playable** | D3 | Easier than the X360 ReXGlue version today |
| Splinter Cell: Double Agent | XBERecomp · — · Not stated (431★) | D4 | Renderer unlisted in catalog row — audit first |
| SSX Tricky | xboxrecomp · **D3D11** · Not stated | D3 | Course-based, contained |
| Star Wars Ep. III: RotS | **Native execution, 32-bit, D3D9** · In-game | **BX** | 32-bit cannot run in x64-only UWP; needs a recomp approach instead |
| Tenchu: Return from Darkness | XboxXBERecomp · D3D12/Vulkan · **Playable** | D4 | Playable helps; runtime gate remains |
| LOTR: Return of the King | XboxXBE-Recomp (Athelas) · D3D12/Vulkan · Not stated | D4 | Launcher bundles PC-version enhancements — untangle |
| LOTR: The Two Towers | (same Athelas) | D4 | — |
| TimeSplitters 2 | DirectXbox-Recomp · Vulkan · In-game | D4 | Own toolchain = own runtime port; split-screen suits Xbox |

## PlayStation 4 — 20 games / 39 ports (native execution)

Same ISA, hostile everything else: PS4 syslibs, GNM→Vulkan→(Dozen|D3D12), guest-memory paging. Small 2D = D4, AAA = D5. No instructions for obtaining dumps/pkg keys are given here — own-copy requirement stands.

| Game | Best starting port | Xbox diff. | Why |
|---|---|---|---|
| Astrea | psport (general bbport layer) · Linux Vulkan · Not stated | D5 | 1★ general-layer experiment, no Windows build |
| Atelier Ayesha DX | psport · Linux · In-game | D5 | As above (also: native PC release exists outside catalog) |
| Atelier Ryza | psport · Linux · In-game | D5 | As above |
| Bloodborne (×16) | bbport family · Vulkan · Playable (multiple forks) | D5 | The flagship trap: 16 forks, zero Xbox builds; memory + shader scope = gow3_xbox-class effort × bigger game. Possible in principle (pattern proven), extreme in practice |
| Crash Team Racing NF (×2) | Native exec · **Vulkan + D3D11** · **Playable** | D4 | D3D11 renderer + kart scope = least-bad PS4 AAA-adjacent; P2P MP audit |
| Dragon's Crown Pro | Native exec · Vulkan · Not stated | D4 | 2D — best PS4 starter with Odin Sphere |
| Driveclub (×2) | Native exec · Vulkan · In-game | D5 | Streaming racer, wheel FFB dead on UWP, DLSS out |
| EA Sports UFC 4 | Native exec · — · **Playable** | D4 | Arena scope; renderer unlisted — audit first |
| Fist of the North Star: LP | bbport · Vulkan · Not stated | D4 | Yakuza-engine city scope keeps it high |
| God of War III Remastered | Native exec (gow3_pc) · Vulkan · In-game | **D1** | Xbox fork already alpha (see D1 table) |
| Gravity Rush 2 | Native exec · Vulkan · In-game | D5 | Open world + motion controls remap |
| inFAMOUS First Light | iss_pc-based · Vulkan · In-game | D5 | Open-world, inherits Second Son framework state |
| inFAMOUS Second Son (×2) | Native exec · Vulkan · In-game | D5 | Open world + touchpad/motion emulation |
| Kamen Rider: MoH | shadPS4-runtime · Vulkan · Not stated | D4 | Arena-action scope |
| Odin Sphere Leifthrasir | Native exec · Vulkan · Not stated | D4 | 2D Vanillaware — do this before any 3D PS4 game |
| SaGa Emerald Beyond | psport · Linux · Not stated | D5 | General-layer, no Windows |
| Shadow of the Colossus (PS4) | Native exec · Vulkan · In-game | D5 | Frame-gen (DLSS-G/FSR3) features need rework; huge world streaming |
| Tales of Symphonia Remastered | psport · Linux · Not stated | D5 | General-layer (and multiplatform elsewhere) |
| The Last Guardian (×2) | Native exec · Vulkan · In-game | D5 | Streaming + creature-AI perf on PC already delicate |
| WipEout Omega Collection | gow3_pc-framework · Vulkan · In-game | D4 | Framework sibling already runs on Xbox (gow3) — best D4 bet in PS4 3D |

## Nintendo 64 — 28 games / 29 ports (easiest family overall)

Family recipe proven (see toolchain table). D2 = Windows/RT64 + Playable/Not-stated; D3 = In-progress/In-game or platform quirks.

| Game | Port · status | Xbox diff. | Note |
|---|---|---|---|
| AeroGauge | N64Recomp · Not stated | D2 | — |
| Aidyn Chronicles | N64Recomp/RT64 · In progress | D3 | Big RPG, PC port still moving |
| Automobili Lamborghini | Static recomp · Not stated | D2 | Confirm RT64 host (toolchain column generic) |
| Banjo-Tooie | N64Recomp/RT64 alpha · In progress | D3 | Large game; alpha |
| BattleTanx | N64Recomp · Not stated | D2 | CI multi-OS incl. Windows |
| BattleTanx: Global Assault | N64Recomp RT64 D3D12 · In-game | D3 | Decomp-based variant exists in its notes |
| Blast Corps | N64Recomp Vulkan · Not stated | D2 | RT64 stack underneath |
| Bomberman 64: 2nd Attack | N64Recomp · Linux-only listing · Not stated | D3 | Windows build first (should be trivial for this stack) |
| Conker's Bad Fur Day | N64Recomp D3D12/Vulkan · Not stated | D2 | Adult content aside, tech is standard family |
| Diddy Kong Racing (×2) | N64Recomp · Playable (Mac/Linux) / In-game (Win D3D12) | D3 | Merge best-host + best-status; online/LAN audit |
| Int'l Superstar Soccer 2000 | N64Recomp Vulkan/D3D12 · Not stated | D2 | — |
| Mystical Ninja Goemon | N64Recomp RT64 · Not stated | **D1** | UWP fork exists (D1 table) |
| Pokémon Snap | N64Recomp RT64 · Not stated | D2 | On-rails = perf gentle |
| Pokémon Stadium | N64Recomp · **iOS/macOS only** · In-game | D3 | No Windows host yet; Transfer Pak features moot |
| Rampage 2: Universal Tour | N64Recomp RT64 · In-game | D3→2 | Shared Rampage repo |
| Rampage: World Tour | (same repo) | D3→2 | — |
| Snowboard Kids | N64Recomp RT64 · **Playable** | D2 | Save flow already verified on PC |
| Snowboard Kids 2 | N64Recomp RT64 · Not stated | D2 | — |
| Star Wars: Rogue Squadron | N64Recomp RT64 multi-API · **Playable** | D2 | Ignore experimental-RT feature on Xbox (FL11.0 UWP) |
| Super Robot Wars 64 | N64Recomp · Not stated | D2 | Fan-translation packaging is content, not tech |
| Tetrisphere | N64Recomp RT64 · Not stated | D2 | Recompiled RSP audio — test audio path early |
| Zelda: Majora's Mask | Zelda64Recomp RT64 · Not stated (7,583★) | **D1** | UWP fork exists; flagship of the family |
| Virtual Pro Wrestling 64 | N64Recomp RT64 · **Playable** | D2 | AKI wrestling set shares runtime work |
| WCW vs nWo: World Tour | N64Recomp RT64 · Playable | D2 | AKI set |
| WCW/nWo Revenge | N64Recomp RT64 · Playable | D2 | AKI set |
| World Driver Championship | N64Recomp RT64 D3D12 · In-game | D3 | "Experimental" per listing; microcode-heavy original |
| WWF No Mercy | N64Recomp RT64 · Playable | D2 | AKI set |
| WWF WrestleMania 2000 | N64Recomp RT64 · Playable | D2 | AKI set |

## GameCube (7) · Wii (4) · Switch (13)

| Game | Port | Xbox diff. | Why |
|---|---|---|---|
| Eternal Darkness (GC) | DolRecomp+GXRuntime · D3D12/Metal/Vulkan · Not stated | D4 | D3D12 exists; GXRuntime UWP port is the project |
| Gekitou Ninja Taisen! 3 (GC) | gcn-recomp (ClashOfNinja) · Not stated | D4 | One port covers 5 game pages — runtime-first, 4★ early |
| Gekitou Ninja Taisen! 4 (GC) | (same) | D4 | — |
| Mario Kart: Double Dash!! (GC) | gcn-recomp · OpenGL · Not stated | D4 | GL→Mesa or GX rewrite; 8P online won't transfer |
| Naruto: Clash of Ninja (GC) | gcn-recomp · Not stated | D4 | — |
| Naruto: Clash of Ninja EU (GC) | (same) | D4 | — |
| Naruto: Clash of Ninja 2 (GC) | (same) | D4 | — |
| DQ Swords (Wii) | wiikit · OpenGL · In-game (early tutorial) | D5 | Sword-motion→pad is a *design* port, plus early PC state |
| Mario Kart Wii (×2) | WiiCompiled/Aurora · Playable-class | **D1** | Proven 58 fps on Series X (D1 table); builder fork is D3D12/Windows |
| Metroid Prime 3: Corruption (Wii) | Static recomp · D3D12/Vulkan · In-game | D4 | Pointer→stick/mouse mapping exists on PC; pad tuning is the game |
| Wii Party (Wii) | Static recomp · **D3D11**/GL · **Playable** | D3 | D3D11 helps; motion minigames need per-game remaps |
| Devil May Cry (Switch) | nx2apk · **repo gone**, Android tool | **BX** | Gone + wrong target concept |
| Fire Emblem Engage (Switch) | TotK-derived recomp · In-game, **archived** | D5 | First-battle-only on PC |
| Mario Kart 8 Deluxe (Switch) | Static recomp · Vulkan Linux/Android · Not stated | D5 | No Windows host; NVN translation stack |
| Metroid Prime Remastered (Switch) | nxrecomp · Vulkan · Not stated | D5 | Young toolchain |
| Pokémon Legends: Arceus (Switch) | LASRecomp · Not stated | D5 | Open-zone streaming vs 5 GB |
| Pokémon Let's Go Eevee (Switch) | LAS Recomp · Vulkan · In-game | D5 | Motion-catch remap + scale |
| Pokémon Let's Go Pikachu (Switch) | (same) | D5 | — |
| Super Mario Odyssey (×2) | Static recomp Win Vulkan · In-game (ignore iOS fork) | D5 | Kingdoms streaming; Jadyx emulator already on Xbox is the sane route today |
| Smash Bros Ultimate (×2 listings, 1 project) | WindowSmash AArch64 recomp · DX11 · Not stated | D5 | DX11 helps renderer only; ~16 GB content + netplay design vs sandbox/5 GB |
| Zelda: Tears of the Kingdom (×3) | Static recomp · Vulkan · In-game/Not stated (4,452★ lead) | D5 | Largest ask in catalog; choose nothing until PC says Playable |
| Tomodachi Life: LTD (×2) | mk8-recomp Linux alpha / nxnative Apple | D5 | No Windows host in either |
| Xenoblade Chronicles 2 (Switch) | Static recomp · Not stated (6★) | D5 | Enormous JRPG, earliest stage |
| Yo-kai Watch 4++ (Switch) | Static recomp · Vulkan · In-game | D5 | DLSS/PCSS features to strip |

## PS1 (10) · PS2 (15) · PS3 (16) · PSP (10) · Dreamcast/32X/Arcade (5)

| Game | Port | Xbox diff. | Why |
|---|---|---|---|
| Bloody Roar II (PS1) | Static recomp · Not stated | **D1** | Tested on Series X (D1 table); CPU-rendered → measure on S yourself |
| Disruptor (×2) (PS1) | PSXRecomp · **OpenGL** · Not stated | D3 | Apply Bloody-Roar pattern: inert GL → software/D3D presenter |
| Harvest Moon: BTN (PS1) | MIPS→C recomp · **software renderer** · In-game | D2 | Software rendering already = UWP-friendly; memory-card saves trivial |
| Hellnight (PS1) | PSXRecomp · In-game | D3 | Standard PSX pattern, In-game status |
| MediEvil (PS1) | RecompOne · OpenGL · Not stated | D3 | RecompOne Xbox recipe exists (NativeAOT); PAL ES/IT builds only |
| Muppet RaceMania (PS1) | psxrecomp · OpenGL · Not stated | D3 | "TV-friendly launcher" already — good sign |
| Ridge Racer (PS1) | Decomp+recomp · **Playable** | D2 | Small, mature |
| Tekken 3 (×2) (PS1) | psxrecomp · OpenGL · Not stated | D3 | Expanded fork imports arcade data (extra legal/content step); rollback netplay won't transfer directly |
| Wild 9 (PS1) | psxrecomp · OpenGL · Not stated | D3 | Standard pattern |
| WWF SmackDown! 2 (PS1) | RecompOne · OpenGL · Not stated | D3 | RecompOne route as MediEvil |
| Burnout Dominator (PS2) | PS2Recomp · Vulkan · **Playable** | D4 | Best PS2 candidate *if* you insist; XBSX2 exists |
| Cartoon Network Racing (PS2) | PS2Recomp · D3D11/12/Vulkan · Not stated | D4 | Multi-renderer runtime helps audit |
| Devil May Cry (PS2) | PS2Recomp · In progress (intros) | D5 | Nothing to port yet |
| Drakengard (PS2) | Static recomp · In-game (Ch.1) | D5 | Musou crowds + early |
| God of War (×3) (PS2) | PS2Recomp · OpenGL/DX11 · In-game (ship fight) | D5 | VU-heavy; PC still early despite 3 forks |
| God of War II (×2) (PS2) | PS2Recomp · Vulkan/— · In-game | D5 | First-area status |
| Killzone (PS2) | PS2Recomp + **linked PCSX2 libs** · Not stated | D5 | PCSX2 GS dependency = emulator-runtime port, not a recomp port |
| Metropolismania (PS2) | PS2Recomp · In-game | D4 | Gentle sim scope once runtime exists |
| Rogue Galaxy (PS2) | PS2Recomp · Not stated | D5 | Big JRPG |
| Shadow of the Colossus (PS2) | PS2Recomp · Metal/GLES (Mac/Vita) · In-game | D5 | No Windows renderer listed |
| Persona 3 FES (PS2) | PS2Recomp · OpenGL · In-game (no battle SFX) | D5 | Incomplete on PC |
| SOCOM II (PS2) | PS2Recomp · OpenGL · In-game | D5 | Custom online-server integration won't map to sandbox |
| Twisted Metal: Black (PS2) | PS2Recomp · OpenGL · In-game | D4 | Arena scope |
| Valkyrie Profile 2 (PS2) | PS2Recomp · OpenGL · In-game (Ch.1 start) | D5 | Famously GS-abusive original |
| War of the Monsters (PS2) | PS2Recomp · Not stated | D4 | Arena scope |
| Armored Core 4 (PS3) | Static recomp · **D3D11** · Not stated | D4 | Least-bad PS3: D3D11 + mission structure. Still Cell/SPU runtime first |
| Armored Core: For Answer (PS3) | Static recomp · **D3D11** · Not stated | D4 | As above, bigger |
| Bakugan (PS3) | ps3recomp · D3D12 · In-game (arena) | D5 | PPU+SPU recomp early |
| Demon's Souls (×2) (PS3) | ps3recomp · D3D12 · In-game (to 1-1) | D5 | Everyone's dream, nobody's starter |
| Drakengard 3 (PS3) | ps3recomp · **Intro** | D5 | Menus/cutscenes only |
| God of War: Ascension (PS3) | ps3recomp · Vulkan/D3D12 · In-game (~13 fps PC) | D5 | Perf on PC already fails |
| inFAMOUS 2 (×2) (PS3) | ps3recomp · Metal/Vulkan · In-game | D5 | Open world, no Windows-first host |
| Killzone 2 (PS3) | ps3recomp · D3D12 · In-game (level 1) | D5 | SPU showpiece title |
| Killzone 3 (PS3) | ps3recomp · D3D12/Vulkan · In-game | D5 | — |
| Killzone HD (PS3) | ps3recomp · Vulkan · In-game | D5 | Port of a port — use PS2 original thinking instead |
| PS All-Stars BR (PS3) | ps3recomp · D3D12 · In-game | D5 | Arena scope can't save Cell runtime cost |
| Ratchet & Clank: ToD (PS3) | ps3recomp · D3D12 · In-game | D5 | Insomniac SPU engine |
| Shadow of the Colossus (PS3) | ps3recomp · D3D12 · In progress (boot) | D5 | Boot only (PS4 version is D5 but saner) |
| Soulcalibur II HD (PS3) | ps3recomp · Metal/Vulkan/D3D12 · Not stated | D5→4 | Fighting-game scope = first PS3 target *after* runtime matures |
| Tony Hawk's Project 8 (PS3) | ps3recomp · DX12 · Not stated | D5 | Lua mod API = sandbox audit plus Cell |
| White Knight Chronicles II (PS3) | PS3Recomp · Vulkan/DX12 exp. · In-game | D5 | Early + huge JRPG |
| Fate/unlimited codes (PSP) | PSPRecomp · Not stated | D3 | Fighter; PSP-family pattern + Windows host work |
| God of War: Chains of Olympus (PSP) | Static recomp · D3D12/Vulkan · In-game | D3 | Shares GoW-PSP port with below; D3D12 available |
| God of War: Ghost of Sparta (PSP) | (same) | D3 | — |
| GTA: Chinatown Wars (PSP) | Static recomp · In-game (5 missions) | D3 | Top-down = gentle; touch minigames heritage check |
| Monster Hunter Freedom Unite (PSP) | Static recomp · **Playable** start-to-finish SP | D3 | Ad-hoc MP is the project; SP port is straightforward-hard |
| Monster Hunter Portable 3rd HD (PSP) | Yakumo · Vulkan/SDL3 · Playable | **D1** | Tested on Series X (D1 table) |
| Pro Evolution Soccer 6 (PSP) | psprecomp · Android-first GL · Not stated | D4 | No Windows-first host |
| Tekken 6 (PSP) | PSPRecomp · **Android-only** · In progress | D5 | Wrong host + early |
| Tekken: Dark Resurrection (PSP) | Static recomp to C/Wasm · GL/WebGL · In-game | D3 | Clean C output is portable; needs new D3D presenter |
| Wipeout Pure (PSP) | PSPRecomp · Metal/Vulkan · **Playable** | D3 | Dozen route (MHP3rd proves the plumbing) |
| Blue Stinger (DC) | DCRecomp · Vulkan · In-game | D4 | SH-4/PowerVR runtime first |
| Sonic Adventure (DC) | KatanaRecomp · D3D11/Vulkan · **Playable** (dev paused) | D3 | D3D11 + Playable; paused upstream. (A DX PC version exists outside catalog — different project) |
| Space Channel 5 (DC) | Static recomp **uses Flycast components** | D4 | Emulator-component hybrid; rhythm timing on TV latency |
| Knuckles' Chaotix (32X) | Static recomp to C++ · **Playable**, multi-OS | D2 | 2D, tiny — easiest non-N64/PS1 row in the catalog |
| Initial D Arcade Stage 3 (NAOMI 2) | SH-4 recomp · Vulkan · In progress | D5 | Arcade I/O (wheel/card) + early; BIOS-free claim needs your legal audit |

---

# Rankings & strategy

**Easiest 15 (do in this order):** Bloody Roar II (done) → Mario Kart Wii (done) → MHP3rd HD (done) → Majora's Mask* → Knuckles' Chaotix → Ridge Racer PS1 → Harvest Moon BTN → any Playable AKI wrestling N64 (No Mercy set) → Snowboard Kids → Rogue Squadron 64 → Crystal Defenders → Call of Duty 3 (D3D11 port) → DOA3 / Blood Wake (first OG-Xbox runtime) → Wii Party → Sonic Adventure DC. (*fork-verify first.)

**Hardest 10 (do not start):** Tears of the Kingdom · Bloodborne (any of 16 forks) · Demon's Souls PS3 · Killzone 2 PS3 · God of War Ascension PS3 · Smash Ultimate · Forza Horizon · Crackdown/Saints Row (open-world + early ReXGlue) · Guitar Hero II/Metallica (peripheral wall) · Fire Emblem Engage (archived, first-battle).

**Highest-leverage projects (port the runtime, inherit the library):**
1. **ReXGlue UWP runtime** (`worleydl/rexglue-sdk-dev` uwp-compat is 8 commits in) — productionizing it moves ~90 games from D4 to D3 and small XBLA titles (Geometry Wars 2, PvZ, BK promos) to D2-territory. This is the single best investment in the catalog.
2. **xboxrecomp D3D11 host to UWP** — unlocks the OG-Xbox D3 cluster (DOA/Blood Wake/SSX/Midtown).
3. **Generic Dozen-on-UWP test + FFmpeg-UWP** (already exist inside mhp3rd-xbox — extract/reuse) — every Vulkan-only row (PSP/PS2/PS4/Xenon) needs exactly these two.
4. **N64 family upkeep** — track worleydl's rt64/plume forks per-game; each new N64Recomp release is then a D2 weekend-class adaptation, not research.

**Reality checks before choosing any row:**
- Is it already back-compatible / natively sold for Series (retail mode)? If yes, Dev Mode port = mods/learning only. (Verify per title in the Store — I have not audited BC status game-by-game.)
- Is an emulator already on Dev Mode better (PS2→XBSX2, Switch→Jadyx, PS1/N64→RetroArch/DuckStation-class)? A recomp port must beat it on perf, mods, or input — otherwise you're porting for sport (valid, but say so).
- Series S: no D1 recipe has tested it. Budget resolution/memory for S or declare X-only honestly like jajdp does.
- License: several upstreams declare **no license** (recipe authors therefore publish *descriptions*, not patched code). You may always patch your own checkout for personal use; redistributing builds is a different legal question — read each repo.

*Method note: catalog data from full 22-chunk fetch of ports.matheusbrauna.com.br + /about/ (2026-11-04); toolchain/Xbox-precedent verification via GitHub API (rexglue-sdk, XenonRecomp, N64Recomp, worleydl/jajdp repo inventories and READMEs quoted). Game-page counts reconcile: 99 X360 + 26 OG + 20 PS4 + 28 N64 + 16 PS3 + 15 PS2 + 13 Switch + 10 PS1 + 10 PSP + 7 GCN + 4 Wii + 3 DC + 1 32X + 1 NAOMI2 = 253.*
