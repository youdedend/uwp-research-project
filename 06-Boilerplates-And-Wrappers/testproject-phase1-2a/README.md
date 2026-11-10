# Test-project Phase 1 / Stage 2a — Pre-allocation recovery ladder (item 2)

> **STEP-1 UPDATE (2026-11-10):** the branch now carries `d31be49` = this 2a commit PLUS the
> item-2 step-1 o1heap staging arena (xbox-swap study). To publish BOTH in one push use the
> newer files in this folder: **`phase1-2a-step1.bundle` + `release-2a-step1.ps1`** (one
> PowerShell paste, same mechanics) and read `release-notes-step1.md` (hardware measurement
> plan + `staging_arena=0` rollback). `bb-port-phase1-2a-step1-kit.zip` bundles them for a
> USB stick. The 2a-only files below remain valid if you want the ladder alone.

> **Release status (2026-11-07):** implementation complete, host tests PASS, prepared as local
> commit `681384b` on `arena/8ac58bdb-test-project` (base `cac48ea`) in the working clone — but
> the push and the Git Data API route are both refused for this session's GitHub credential
> ("Resource not accessible by integration" = app token scoped to `uwp-research-project` only).
> **One `git push origin arena/8ac58bdb-test-project` after the GitHub connection is refreshed
> releases it** (the `Xbox build` workflow publishes the `[release]` pre-release automatically).

**What:** the safe first half of follow-up item 2 for `youdedend/Test-project` (Bloodborne Xbox
UWP): the ordered reclaim ladder runs **before** a DeviceLocal allocation crosses the 250 MiB
reserve floor, instead of only after one fails. It frees memory; it **never refuses** an
allocation — denial/split/skip stays stage 2b until caller contracts exist (per the handoff
"Safe continuation for item 2").

**Target:** `youdedend/Test-project` branch `arena/8ac58bdb-test-project` @ `cac48ea`.
**Patch:** `phase1-2a-recovery-ladder.patch` (9 files, +308 lines, produced by `git diff`
against `cac48ea` and applied with `git apply`).

## What the patch does

| File | Change |
|---|---|
| `xbox/graphics/arena_admission_policy.h` | adds `ShouldRecover()` — the item-2 trigger: ≥ 16 MiB (`kMinimum`) DeviceLocal request that would leave < 250 MiB (`kHeadroom`) of the 5,120 MiB budget. **Previously `kHeadroom` was computed nowhere in production code.** |
| `xbox/graphics/recovery_ladder.h` (new) | pure ordered-rung engine: `FinishGpu → PopPending → ReleaseRetired → ReclaimImages → Pager`, early-exit when the need is covered (the 10 s reclaim-walk stall in hardware-test-18 is why), `mid_draw` skips Finish (handoff failed-attempt #5), null hooks safe, `need=0` no-op. |
| `gpu/shim/bbgpu.cpp` | `bbgpu_uwp_prealloc_ladder(need, flags)` — real rungs: `GetScheduler().Finish()` (flag-gated), `PopPendingOperations()`, `ReleaseRetiredArenas` + staging idle trim, `TextureCache::EmergencyReclaim`, `runtime_memory_page_out`. One summary log line. |
| `gpu/shadps4/video_core/buffer_cache/buffer.cpp` | pre-alloc trigger just before `vmaCreateBuffer`: `ShouldRecover(...)` → ladder with `mid_draw=1` (this ctor is reached from `GetDenseArena` after `BeginRendering`). Existing headroom/emergency/over-budget paths untouched. |
| `xbox/graphics/dense_buffers.cpp` | **pre-merge reclaim**: when the arena live-cap projection fails, release retired arenas + take collectible images *before* the merge allocates its transient peak (the `.819` "live=912 retired=448" case) — then proceed regardless. Pager deliberately excluded here: `runtime_memory_page_out` takes the commit lock the guest fault path uses (Test #22's 10 s stall). |
| `xbox/platform/main.cpp` | new switch `arena_admission_recover` (ini) → `BB_ARENA_ADMISSION_RECOVER` (env), default `1` (on) — this is item 2's requested behavior; set `0` to restore today's exact behavior. |
| `xbox/tests/recovery_ladder_test.cpp` (new) + `arena_admission_policy_test.cpp` | pins rung order, mid-draw Finish skip, early exit, still-short accounting, no-ops; `ShouldRecover` arithmetic. Registered in `.github/workflows/xbox.yml`. |

## Standing rules honored

- No allocation is ever denied, split or skipped (no caller-contract invention). The unmodified
  `ASSERT_MSG(result == VK_SUCCESS, ...)` remains the final stop.
- Finish rung skipped mid-draw (failed-attempt #5); `extern "C"` only at namespace scope
  (failed-attempt #4); `EmergencyReclaim(0)` never used as "free everything" (existing footgun);
  `slot_vector.h` and all assertions untouched; non-UWP paths unchanged (all new code under
  `BB_UWP` or the `xbox/` tree).

## Validation status (honest)

- **Host tests: PASS locally** (`g++ -std=c++20 -Wall -Wextra`):
  `recovery_ladder: all checks passed` · `arena admission arithmetic: all checks passed`
  (the second suite's existing checks plus 6 new `ShouldRecover` cases).
- **Windows/clang-cl compile of `buffer.cpp` / `bbgpu.cpp` / `dense_buffers.cpp` / `main.cpp`:
  NOT built here** (no Windows SDK in the sandbox) — CI's "Xbox UWP package" job validates on
  push. Treat a red CI as a code-review input, not a surprise.
- **No MiB saved is claimed.** Per the project's own rule, benefit claims need the console run.

## Apply (from a `Test-project` checkout on `arena/8ac58bdb-test-project` @ `cac48ea`)

```bash
git apply --check 06-Boilerplates-And-Wrappers/testproject-phase1-2a/phase1-2a-recovery-ladder.patch  # path as placed
git apply     <...>/phase1-2a-recovery-ladder.patch
g++ -std=c++20 -I xbox/graphics xbox/tests/recovery_ladder_test.cpp -o /tmp/rlt && /tmp/rlt
g++ -std=c++20 -I xbox/graphics xbox/tests/arena_admission_policy_test.cpp -o /tmp/aap && /tmp/aap
git checkout -b <work-branch> && git commit   # then push to arena/8ac58bdb-test-project per house rules
```

## Test #30 acceptance (console, Series S)

1. `loader.log` gains `UWP recovery ladder (pre-alloc): reserve floor hit ... freed N MiB`
   **before** memory pressure peaks; `UWP memory emergency (allocation failed)` lines should
   become rarer, not louder.
2. World-load merges log `UWP arena admission: reclaimed N MiB before merge ...`; the
   `.819`-class "live=912 retired=448" shape should shrink (retired bytes drain while allocs wait).
3. No new fault RVAs (`+0x3003f0/+0x26bbb7/+0x27222e/+0x272f1c`), `corrupt=0`, no new stalls:
   the ladder must never be seen taking > ~250 ms on the pre-alloc path (it early-exits).
4. Steady-state Yharnam ≤ 3,500 MiB with ≥ 200 MiB headroom is the goal; report the measured
   curve either way. `arena_admission_recover=0` is the A/B switch for a matched run.

## What this is NOT

Not stage 2b (no split/skip/deny), not the 700–800 MiB live-cap enforcement beyond
reclaim-before-merge, not a claim of any measured saving, not hardware-validated.
