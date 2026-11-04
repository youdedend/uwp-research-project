# Patch series rules

Patches live here as small, numbered, anchored diffs against the exact commits in `../sources.lock.json` — never as a forked copy of the upstream trees in this repo.

## Landed

| Patch | Target | Status |
|---|---|---|
| [`0001-aurora-store-detection.patch`](0001-aurora-store-detection.patch) | NSMBW `v0.3.1` `aurora-main/CMakeLists.txt`, `aurora-main/cmake/aurora_core.cmake` (+18/−1) | Written 2026-11-04. `git apply --check` + apply verified on a clean pinned clone (tree restored after). CMake detection/defaults only. **PC build gate still pending** — not yet configured/built anywhere |

Apply from this repository’s root (patch paths are relative to the NSMBW repo root — no `--directory`; the `..\..\patches` argument is resolved from inside the `-C` clone directory):

```powershell
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply --check ..\..\patches\0001-aurora-store-detection.patch
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply ..\..\patches\0001-aurora-store-detection.patch
```

## Series plan

| Series | Target tree | Contents | Spec |
|---|---|---|---|
| `0001…0006` | `aurora-main/` inside NSMBW `v0.3.1` | Store detection → providers → extern hygiene → paths → window/surface/input → system-info/GPU | [`../AURORA-REBASE.md`](../AURORA-REBASE.md) |
| `0101…` | `runtime/` inside NSMBW `v0.3.1` | Log-first entry glue, paths, fibers/exception declarations, feature exclusions | [`../overlay/README.md`](../overlay/README.md) |
| `0201…` | build glue | Store compile replay, AppContainer link, package staging (our own scripts; MIT-recipe tooling may be adapted with notices intact) | [`../BUILD-ORDER.md`](../BUILD-ORDER.md) Phases 2–4 |

## Rules

1. **Anchored and idempotent-aware:** every patch must apply with `git apply --check` to a *clean* pinned checkout, in series order. If an anchor drifts, stop and update the spec — never widen context until it “applies.”
2. **Defines or it didn’t happen:** Aurora deltas behind `AURORA_WINDOWS_STORE`, runtime deltas behind `NSMBW_UWP`. After each patch, the PC build (Phase 1) is re-run; a patch that changes PC behavior is split or reverted.
3. **One concern per patch:** providers are not merged with surface changes; fibers are not merged with paths. The Series S will produce confusing failures — bisectable patches are the only way back.
4. **License hygiene:** NSMBW/WiiCompiled are GPL-3.0 (our patches to them are published under GPL-3.0); Aurora and the jajdp recipe are MIT (keep `© 2022 Luke Street` / recipe notices with derived Aurora patch work). No upstream source files are copied into this folder — patches and new overlay files only.
5. **No game-derived content:** generated/translated code, extracted assets, saves, and built binaries never enter a patch, a test fixture, or this repository.
6. **Evidence attached:** each landed patch gets a line in `../STATUS.md` with the gate it passed (PC build, Store compile histogram delta, or on-console log excerpt *summary* — logs themselves stay out of Git if they contain user paths).
