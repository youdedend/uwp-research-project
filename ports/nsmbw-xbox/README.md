# New Super Mario Bros. Wii → Xbox Series S (Developer Mode UWP)

**Status: Phase 1 ready to run on the Windows build PC; no Xbox build exists yet.** Phase 0 pinning/audit is complete, the first small Aurora patch (`0001`) is written and apply-verified, and `tools/run-phase1-pc.ps1` now encodes the pristine upstream PC baseline (translator → shards → configure → build → `compile_commands.json`). This folder does **not** contain the game, extracted game files, generated game code, prebuilt UWP libraries, certificates, or a ready-to-install package. See [`STATUS.md`](STATUS.md) for the exact evidence boundary.

## The port in one paragraph

We are adapting WitherBlitz's **NSMB-Wii-Multiplayer-Recompilation `v0.3.1`** (GPL-3.0), a WiiCompiled/Aurora-family static recompilation of *New Super Mario Bros. Wii*, to run as an **x64 UWP AppContainer package on an Xbox Series S in Developer Mode**. The engineering template is jajdp's **retro-rewind-xbox** recipe, which proved the same runtime family on a **Series X** — its author is explicit that a **Series S was never tried**, so Series S memory/performance is our unknown to measure, not a promise inherited from that project.

## First milestone (and what is deliberately out)

**v1 target:** couch/local play only — title screen → World 1-1 → save → relaunch → save still there → 30-minute standalone soak on the Series S with no debugger attached.

**Deferred until after v1:** LAN/Tailscale netplay, self-updater, desktop launcher/folder picker, mods/texture packs, Discord presence, bug-for-bug PC settings UI, and the separate *Newer* (`SMNE03`) build.

## Non-negotiable input

The upstream build runs only **USA `SMNE01` revision 1**. You must supply your own legally obtained copy; this repository will not store a disc image, extracted assets, generated code, saves, or built packages. The project owner confirmed on 2026-11-04 that they have that exact revision, the Series S is in Developer Mode, and a Windows PC with Visual Studio 2022 is available. Upstream’s `unpack_game.py` still validates the extracted folder and clean `main.dol` during the build. Nothing here explains how to dump, decrypt, or bypass protection on a game disc.

## Quick start (Windows build PC)

Prerequisites for the Phase 1 PC baseline: Git, Python 3, and the **.NET 8 SDK**, plus your extracted exact-revision game folder outside tracked files. Later phases additionally need Visual Studio 2022’s C++ UWP “store” environment and Windows SDK `makeappx`/`signtool`; see [`BUILD-ORDER.md`](BUILD-ORDER.md).

```powershell
# From the repository root: bootstrap + audit + upstream portable tools/deps +
# game validation + translator + pristine PC build + compile_commands.json.
powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\run-phase1-pc.ps1 `
  -GameDir "D:\Path\To\Extracted\SMNE01-rev1" `
  -WithBaseline -CreateGameLink
```

Then play `work\NSMB-Wii-Multiplayer-Recompilation\native-build\WiiCompiled.exe` through the manual gate in `BUILD-ORDER.md`: title -> World 1-1 -> save -> relaunch -> save persists. To run only the pinned clone/audit step:

```powershell
powershell -ExecutionPolicy Bypass -File ports\nsmbw-xbox\tools\bootstrap.ps1 -WithBaseline -Audit
```

Equivalent cross-platform form:

```powershell
python ports\nsmbw-xbox\tools\bootstrap.py --with-baseline --audit
python ports\nsmbw-xbox\tools\audit_uwp.py `
  --nsmbw ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation `
  --recipe ports\nsmbw-xbox\work\retro-rewind-xbox `
  --wiicompiled-v0231 ports\nsmbw-xbox\work\Wiicompiled-v0.2.31 `
  --out ports\nsmbw-xbox\reports\phase0-audit-local.md --check
```

Then read, in order: [`STATUS.md`](STATUS.md) → [`AURORA-REBASE.md`](AURORA-REBASE.md) → [`BUILD-ORDER.md`](BUILD-ORDER.md) → [`overlay/README.md`](overlay/README.md) → [`package/README.md`](package/README.md).

## GitHub Actions coverage

The repository-level workflow [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs on every push and pull request, and can be started manually from GitHub's Actions tab. It exercises every script currently committed here:

- repository validation (Python syntax, JSON/TOML/XML parsing, Markdown links, lock-file pins/hashes, forbidden game/binary artifacts) plus both Python CLIs' `--help` entry points;
- parsing of every PowerShell script with Windows PowerShell on `windows-latest`;
- on Ubuntu, the real pinned-source bootstrap with the WiiCompiled baseline, the read-only UWP audit, and a check/apply/diff of patch `0001` in a disposable clone;
- on Windows, the real `bootstrap.ps1` and pinned audit, .NET 8 setup, and `run-phase1-pc.ps1 -CheckOnly` against an empty layout-only fixture.

That Windows job is a script/prerequisite test, **not** a game build: GitHub-hosted runners have no access to the owner's extracted `SMNE01` rev 1 folder, and this public repository must never receive it. Full translation/build/gameplay and all Series S testing still require the local Windows PC/console flow above (or a private self-hosted runner that already has the owner's game folder).

## Layout

| Path | Purpose |
|---|---|
| [`sources.lock.json`](sources.lock.json) | Exact repos, tags/commits, licences, roles, confirmed inputs, and the two-pin UWP prebuilt split |
| [`STATUS.md`](STATUS.md) | Living engineering ledger: verified facts, blockers, next action |
| [`AURORA-REBASE.md`](AURORA-REBASE.md) | Why the proven 22-file Aurora patch cannot be force-applied, and the file-by-file semantic rebase |
| [`BUILD-ORDER.md`](BUILD-ORDER.md) | Runtime-first phases and go/no-go gates from PC build to Series S soak |
| [`tools/bootstrap.py`](tools/bootstrap.py) / [`bootstrap.ps1`](tools/bootstrap.ps1) | Pinned clone + verification into ignored `work/` |
| [`tools/audit_uwp.py`](tools/audit_uwp.py) | Read-only pin check, patch dry-run, desktop-API inventory |
| [`tools/run-phase1-pc.ps1`](tools/run-phase1-pc.ps1) | Windows-only pristine PC baseline: prerequisites, bootstrap, upstream tools/deps, game validation, translator, build, compile-database capture, local JSON report |
| [`overlay/README.md`](overlay/README.md) | Entry-point, logging, path, and feature-exclusion design for our new code |
| [`patches/README.md`](patches/README.md) | Patch-series rules + landed patches (small, anchored, behind defines, PC build stays green). First patch written: `0001-aurora-store-detection.patch` — applies cleanly, build gate pending |
| [`package/`](package/README.md) | Unvalidated manifest/config templates and the `LocalState` layout contract |
| [`reports/`](reports/2026-11-04-phase0-audit.md) | Dated Phase 0 audit evidence plus the fill-in Phase 1 PC report template |

## Licensing posture

- NSMBW upstream and WiiCompiled are **GPL-3.0**; patches we publish against them must respect that.
- Aurora and the jajdp recipe/tooling are **MIT**; keep their notices with derived patch/tool work.
- UWP prebuilt bundles are pinned and partially inspected (layout, bundled component licences, SHA-256 hashes, PE imports), but `sources.lock.json` still marks them “verify before use” because no Windows Store link has run. In particular, do **not** use the main bundle’s desktop-linked SDL; use the separately pinned `_APP` SDL. Do not redistribute third-party DLLs from this repo.
- Package tiles must be your own placeholder art. No Nintendo artwork, screenshots, or logos belong in a shareable package.
