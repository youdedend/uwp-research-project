# Patch series rules

Patches live here as small, numbered, anchored diffs against the exact commits in `../sources.lock.json` — never as a forked copy of the upstream trees in this repo.

## Landed

| Patch | Target | Status |
|---|---|---|
| [`0001-aurora-store-detection.patch`](0001-aurora-store-detection.patch) | NSMBW `v0.3.1` `aurora-main/CMakeLists.txt`, `aurora-main/cmake/aurora_core.cmake` (+18/−1) | Written 2026-11-04. `git apply --check` + apply verified on a clean pinned clone (tree restored after). CMake detection/defaults only. **PC build gate still pending** — not yet configured/built anywhere |
| [`0002-aurora-uwp-dep-providers.patch`](0002-aurora-uwp-dep-providers.patch) | NSMBW `v0.3.1` Aurora provider layer: new `cmake/AuroraUwpDep.cmake`, Dawn/SDL/nod provider branches, provider enum/defaults, one Store-only include from `extern/CMakeLists.txt` (+287/−10) | Written after `0001`. Series apply (`0001` then `0002`) and `git diff --check` verified on a clean pinned clone. CMake module/provider logic was exercised in synthetic local harnesses: missing SDL root fails closed; layout fixtures select `uwp_dep` and create `dawn::webgpu_dawn`, `SDL3::SDL3`, `nod::nod`, and `aurora::uwp_dep`. **No real UWP compile/link or PC rebuild gate has run yet**. SDL must come from the separate true-UWP checkout; the main bundle's desktop SDL is explicitly rejected by design |

Apply from this repository’s root, in series order (patch paths are relative to the NSMBW repo root — no `--directory`; the `..\..\patches` argument is resolved from inside the `-C` clone directory):

```powershell
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply --check ..\..\patches\0001-aurora-store-detection.patch
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply ..\..\patches\0001-aurora-store-detection.patch
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply --check ..\..\patches\0002-aurora-uwp-dep-providers.patch
git -C ports\nsmbw-xbox\work\NSMB-Wii-Multiplayer-Recompilation apply ..\..\patches\0002-aurora-uwp-dep-providers.patch
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
