# Xbox Developer Mode Porting — Research & Learning Project

**Goal:** Learn how to assess and, where feasible, adapt a game you own the source to for **Xbox Series X|S in Developer Mode (UWP, personal/testing use)** — and understand Direct3D 12 only where it actually applies.

**Your current inputs (2026-11-04):** Active port = *New Super Mario Bros. Wii* (exact USA `SMNE01` revision 1 confirmed) · "learn everything", research track completed through PS3/PS4/Switch · Target = **Xbox Series S** in Dev Mode (confirmed) · Build PC = Windows + Visual Studio 2022 (confirmed) · Experience = treat as beginner (expert-led pacing). Docs 01–04 were written Series X|S-generic; doc 05 is the Series S-specific pass.

> This repo is a study handbook built from a live review of all 32 links you supplied (READMEs, licenses, releases, repo structure, activity — checked via GitHub API + page fetches on 2026-11-04). It separates **official Microsoft guidance** from **community/hobby projects**. Community repos are treated as *case studies*, not proof that your future game will port the same way.

## Read in this order

| # | File | Covers (your A–L format) |
|---|---|---|
| 1 | [`docs/01-feasibility-sources-case-studies.md`](docs/01-feasibility-sources-case-studies.md) | A Feasibility · B Source inventory (all 32) · C Case studies · D Compatibility matrix |
| 2 | [`docs/02-strategy-roadmap-d3d12.md`](docs/02-strategy-roadmap-d3d12.md) | E Strategy · F Roadmap/milestones · G D3D12 concepts · H Language/engine examples |
| 3 | [`docs/03-troubleshooting-testing-learning.md`](docs/03-troubleshooting-testing-learning.md) | I Troubleshooting · J Testing/optimization · K Exercises + answer key · L Readiness checklist |
| 4 | [`docs/evidence-table.md`](docs/evidence-table.md) | One-row-per-source evidence: license, activity, target/API evidence |
| 5 | [`poc/README.md`](poc/README.md) | Smallest proof-of-concept spec (do this before any full port) |
| 6 | [`docs/04-native-ports-xbox-difficulty.md`](docs/04-native-ports-xbox-difficulty.md) | **All 253 games / 304 ports** from ports.matheusbrauna.com.br rated D1–D5/BX for Xbox Dev Mode, by toolchain family |
| 7 | [`docs/05-ps3-ps4-switch-deep-dive.md`](docs/05-ps3-ps4-switch-deep-dive.md) | **PS3 / PS4 / Switch deep dive for Series S**: all 49 catalog games re-assessed S-specifically, play-vs-port-vs-research routes, Xbox-side emulators (RPCS3-xbox, CellBox, shadPS4 attempts, Jadyx), go/no-go gates, 90-day plan |

## The 30-second verdict

- **The game is chosen and Phase 1 is ready to run.** *New Super Mario Bros. Wii* (NSMB-Wii-Multiplayer-Recompilation `v0.3.1`, GPL-3.0; owner's USA `SMNE01` rev 1 copy, Series S Dev Mode, and VS2022 PC confirmed) is being adapted in [`ports/nsmbw-xbox/`](ports/nsmbw-xbox/README.md). The pristine PC baseline script now encodes upstream's required validate -> prelink -> translate -> build order. The proven Mario Kart UWP Aurora patch **does not apply** to NSMBW's customized Aurora, so after the green PC control build the port proceeds as a deliberate semantic rebase. No Xbox build exists yet; this remains a D3 (hard) project until a Store-environment compile histogram and Series S measurements say otherwise.
- **Dev Mode ≠ commercial Xbox development.** Dev Mode on a retail console runs **UWP (AppContainer, x64)** packages for personal testing. Commercial Store games use the **GDK/GDKX + ID@Xbox** route — different SDK, packaging, certification, and hardware access. Unity/Defold "Xbox support" and The Forge's console backends belong to that commercial route, **not** Dev Mode sideloading.
- **Direct3D 12 *is* available to UWP on Series X|S** (Feature Level 11.0 per Microsoft's archived UWP-on-Xbox resource page), but that does **not** mean you should write a D3D12 renderer. Most successful Dev Mode case studies avoid hand-written D3D12: they reuse D3D11, OpenGL-via-Mesa/ANGLE, Vulkan-via-Dozen, WebGPU-via-Dawn, or SDL's renderer — and pay for it in shader-translation and memory pain instead.
- **Binary-only games cannot be ported** in any practical/legal sense covered here. You need source + permission + rebuildable dependencies. See §A.4.

## Automated checks

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the repository validator, both Python tool entry points, Windows PowerShell parsing for every `.ps1`, the pinned-source bootstrap and UWP audit on Ubuntu and Windows, a disposable apply-check for Aurora patch `0001`, and the NSMBW Phase 1 script in `CheckOnly` mode. It deliberately does **not** run the real game translation/build: no extracted game belongs in this public repository or on a GitHub-hosted runner. The full game-dependent build remains a local Windows step.

## Safety & legal boundaries

This handbook does **not** cover: obtaining/decrypting copyrighted game dumps, keys, firmware or BIOS files; bypassing DRM, signing, or console security; or redistributing game assets. Emulator/recompilation repos are analyzed only for their *porting architecture* (windowing, input, renderer translation, memory). Always check each repo's license before copying code — "public on GitHub" ≠ "free to reuse."

## Conventions

- **[Verified]** = seen in official docs or directly in repo code/README/releases during review.
- **[Claimed]** = repo/community asserts it; not independently build-tested here. I did not compile these projects or run them on hardware.
- **[Inference]** = my engineering judgment from the evidence.
- Dates are `pushed_at` from the GitHub API at review time; re-check before relying on them.
