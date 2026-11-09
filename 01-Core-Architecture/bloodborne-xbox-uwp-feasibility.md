# Bloodborne → Xbox UWP — Feasibility Dossier (2026-11-07, amended same day)

**Verdict (amended): NO-GO on running the PS4 binary (route B/C) or shipping Sony code/assets.
Route D (native-RE port) is NOT dead — `youdedend/Test-project` runs the game on a Series S
inside the 5,120 MiB budget and is *memory-bound in extended play*, not budget-impossible.
Route E (streaming) remains the zero-engineering route. See the Correction box in Wall 3.**

| Route | Verdict | Constraint (evidence) |
|---|---|---|
| A. Ship Sony code/assets (any sense) | ❌ absolute | Sony/FromSoftware IP; Wall 1 |
| B. Translate the PS4 binary to UWP | ❌ absolute | Orbis ABI ≠ Win32; nothing to map; Wall 2 |
| C. shadPS4 (full emulation) inside UWP | ❌ hard NO | 16–32 GB RAM req vs **5,120 MiB Dev Mode cap**; Vulkan→D3D12 rewrite; Wall 3 |
| D. Native-RE ports (bbport-class) inside UWP | ⚠️ **demonstrated** | User's `youdedend/Test-project` plays on Series S (25.8 FPS Yharnam) inside 5,120 MiB via guest-page swap; extended-play memory wall remains (stalls ~5,055–5,116/5,120 MiB after 800–1,300 presents) |
| E. **Stream from own PS4/PS5 (chiaki-class client)** | ✅ viable | Memory ≈ hundreds of MB; no JIT/Vulkan; **psxbox/XPort exist, unfinished** |

---

## Wall 1 — Legal/ownership (absolute)

Bloodborne is © Sony Interactive Entertainment / FromSoftware. No source code is public and
no license is granted to third parties. Every sense of "port" requires copying their
copyrighted code and/or assets: a straight port copies both; a translation layer hosts a
copied binary; a remake ships copied assets. The entire surviving ecosystem (shadPS4,
chiaki-ng, the unofficial native-port scene) survives on one posture: **reverse-engineered
clean code + user-supplied legally-obtained dump, no Sony code or assets distributed.**
Fan-project enforcement precedent exists in adjacent spaces (Take-Two v. re3/GTA
reverse-engineering project, 2021–2023; the Bloodborne-demake rebrand after Sony contact).
Dev Mode sideloading is a Microsoft developer channel — it grants no Sony rights.
(Not legal advice; the technical program should treat Wall 1 as unmovable.)

## Wall 2 — Nothing to translate (closed binary, foreign ABI)

Our Phase-1 closed-binary finding (Steam 32-bit stub) established: without source, a Win32
binary cannot be responsibly "ported" by API mapping alone. Bloodborne is far worse — it is
not a Windows program at all:

- **Orbis (PS4) OS ABI**: `libSce*` system libraries, Sony-specific loader/relocations.
- **Graphics**: GNM/GNMX (explicit AMD GCN), PSSL-compiled shader binaries — no D3D, no
  Vulkan, no HLSL anywhere in the guest.
- **CPU**: x86-64 (so *instruction* translation is at least possible in principle), but the
  software stack around it shares zero surface with WinRT/UWP.

Consequences: (a) full-system/HLE emulation is the only way to run the binary (Wall 3),
(b) a *native* port means re-implementing the FromSoft engine from scratch — which is
exactly what the unofficial "bbport" community did on PC after years of RE work
(bloodbornepc.wiki, Oct 2026). That is a multi-year, multi-engineer effort producing
Win32+Vulkan software. The user's `youdedend/Test-project` then brought that engine to UWP
— see the Correction box under Wall 3 for how far it actually got.

## Wall 3 — The budget wall (our Dev Mode memory study, the kill-shot)

Dev Mode UWP caps (PRIMARY/corroborated, see
`../03-Memory-CPU-And-JIT/dev-mode-memory-and-system-caps.md`):

- **5,120 MiB total process budget — identical on Xbox One and Series X|S.**
- CPU: 4 exclusive + 2 shared cores (Game class). GPU: shared model, D3D11/12 only.
- **2 GB max per file** in Dev Mode; JIT OK via `VirtualProtectFromApp` (the one open door).

vs. what the candidates actually demand (Oct 2026 sources, [S1][S2][S3]):

| Requirement | shadPS4 + Bloodborne | native ports (bbport-class) | Dev Mode budget |
|---|---|---|---|
| System RAM | **min 16 GB, rec. 32 GB** (own quickstart, "severe memory leaks") | **≥6 GB free (RAM+pagefile)** | **5,120 MiB** |
| GPU memory | rec. **12 GB** (8 GB cards crash in some areas) | Vulkan 1.3 GPU, 2 GB+ | shared pool, no VRAM carve |
| Graphics API | Vulkan 1.3 (+ `VK_KHR_push_descriptor`) | Vulkan 1.3 | **D3D11/12 only — no Vulkan** |
| CPU ISA | x86-64-v3 (AVX, Haswell+) | AVX1/SSE4.2 | Series Zen2 ✅ / One Jaguar ❌ |
| Storage | ~30–50 GB dump, multi-GB `.psarc` chunks | same dump | 2 GB/file ⇒ USB-only layout |

Every row overflows by 3–6× (RAM) or is structurally unavailable (Vulkan). shadPS4's
"Bloodborne" compatibility entry itself is still **"Ingame — serious issues"** [S2].
Phase 1's tentative "shadPS4 doubtful on Series S" is upgraded to **hard NO on all Dev Mode
hardware for route C (full emulation)** — the sandbox is 5 GB everywhere.

> **CORRECTION (2026-11-07) — route D row of this dossier was wrong, falsified by field
> data.** The user's `youdedend/Test-project` (UWP port of `Supermedo/bloodborne_pc`) runs
> the game **on real Series S hardware inside the 5,120 MiB cap**: Central Yharnam live 3D
> gameplay at **25.8 FPS** (`presents=1885`, `UWP swap: out=808 in=250 disk=572`,
> `corrupt=0`), title/menus at 29.4 FPS. Why the "≥6 GB" row misled: (a) the PC figure
> includes pagefile slack, (b) bbport-class is **native x86-64 + HLE**, not full emulation —
> there is no 8 GB guest RAM to host, only pages the game touches, and (c) the port pages
> cold guest pages to a compressed LocalState swap file (Test 27: **1,439 MiB of guest pages
> in a 713 MiB file**). The real constraint is an **extended-play memory wall**: runs stall
> at **5,055–5,116/5,120 MiB** after 800–1,300 presents (Tests 15–29: `vmaCreateBuffer -2`,
> swap-disk ceilings, `VK_ERROR_DEVICE_LOST` at ~4,989 MiB). Remaining engineering gap =
> enforced allocation admission + arena cap (observation-only today) + swap-volume limits.
> Evidence: `youdedend/Test-project` `docs/hardware-test-11…29/`, `handoff.md`,
> `PROJECT_COMPLETE_HISTORY.md` @ `arena/8ac58bdb-test-project`. Field notes in
> `../03-Memory-CPU-And-JIT/testproject-field-notes.md`. Vulkan-on-UWP was solved by
> packaging Mesa Dozen (`vulkan_dzn.dll`) — the "no Vulkan" row needed a translation layer,
> not a rewrite.

## The GO route — stream it (route E)

Bloodborne on an Xbox display does not require Bloodborne code *on* the Xbox: Sony's own
Remote Play streams it from a PS4/PS5 the user owns. Two open-source Xbox UWP clients exist:

1. **`yoni101087/psxbox`** [S4] — "A PlayStation Remote Play client for Xbox (UWP, Dev
   Mode)". chiaki-ng protocol lib (C, clang-cl) → **Media Foundation H.264/HEVC hardware
   decode (D3D11) → SwapChainPanel**, Opus→**XAudio2**, **Windows.Gaming.Input** pad
   mapping. Status: *"first version, never compiled"* — needs a build-fix round + on-Xbox
   testing. LAN-only (PSN-over-internet stubbed out).
2. **`Ibbolufc/XPort`** [S5] (AGPL-3.0) — same architecture via chiaki-ng's `lib/`; status:
   "Milestone 1 … Remote Play itself is not yet wired into the Xbox app."

Why this route survives every audit constraint:

- **No JIT, no Vulkan, no guest memory** — video is *decoded*, not emulated; footprint is
  hundreds of MB against the 5,120 MiB budget. Xbox One is fine.
- Every layer maps onto findings we already hold: WGI pad quirks (drop-in tracker),
  XAudio2 suspend quiesce (audio-notes), Device Portal packaging (our package.ps1 case
  study), B-button/back-suspend handling.
- Legal posture matches the ecosystem: client-only, no Sony code, user's own console+game.
- Open gap worth noting: chiaki needs the PSN **AccountID** (OAuth script) for registration;
  in-app PSN sign-in is a known TODO in psxbox.

## Decision tree (answer to "can you make a port?")

1. Want Bloodborne *code* on Xbox → **no**, walls 1–3 are absolute/structural. Full stop.
2. Want Bloodborne *playable on the Xbox* → **yes, legally and feasibly**: finish/test a
   chiaki-class UWP client (psxbox is closest — code exists, never compiled). Work items:
   build fixes on MSVC/clang-cl + Windows SDK, deploy via Device Portal, round-trip test
   with a real PS4. Not doable inside this Linux sandbox (needs a Windows build host +
   hardware), but source-level fixes/audits are.
3. Future-possible (not for Dev Mode): if Microsoft ever raised the UWP budget or a
   console-native code path appeared (GDK devkits are a different, licensed program), the
   math would be re-run — nothing in this dossier changes short of that.

## Sources

- [S1] shadPS4 official quickstart (RAM 16/32 GB, VRAM 12 GB rec., "severe memory leaks",
  Bloodborne = 1.0 pkg + 1.09 update, user-dump model) — shadps4.org (Oct 2026)
- [S2] bloodbornepc.wiki, "Bloodborne Native Port vs shadPS4" (shadPS4 rating "Ingame —
  serious issues"; native port reqs: 6 GB free mem, AVX1/SSE4.2, Vulkan 1.3; x86-64-v3 for
  shadPS4) — bloodbornepc.wiki/native-port-vs-shadps4/ (Oct 2026)
- [S3] r/bloodborne + bloodbornegame.wiki (community: 16 GB RAM baseline, VRAM crashes at
  1440p even on 16 GB cards) — corroboration of [S1]
- [S4] github.com/yoni101087/psxbox (Xbox UWP Remote Play client; "first version, never
  compiled"; architecture table)
- [S5] github.com/Ibbolufc/XPort (AGPL-3.0 Xbox Series X|S Remote Play client; milestone 1
  shell only)
- Ground truth for the budget column:
  `../03-Memory-CPU-And-JIT/dev-mode-memory-and-system-caps.md` (this repo)
