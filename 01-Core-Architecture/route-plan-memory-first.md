# Route Decision — Bloodborne Xbox UWP (2026-11-07)

**Decision: Memory-first stabilization. Kill the allocation spike → cut steady-state demand
→ ship a stable playable vertical. No architecture pivot, no Series X wait, streaming stays
a side bet only.**

Target "done" for this phase (new acceptance): **character creation → Yharnam → Cleric Beast
area → Hunter's Dream warp → 3 area transitions → 20-minute soak on Series S at 720p/30,
surviving 3 consecutive runs, with ≥ 200 MiB steady-state headroom under 5,120 MiB.**
The wall must be approached with margin, not with 4 MiB to spare.

## Why this route (evidence)

1. The wall is a **spike problem before an average problem**: Test 21 recorded a **+447 MiB
   burst across two presents**; tests 28/29 died at ~5,055–5,116/5,120 MiB with
   **912 MiB live + 448 MiB retired arenas** and only 301 MiB textures. Averages were fine;
   the arena/transient peak crossed the line and `vmaCreateBuffer → -2` / device-lost ended
   the run.
2. **Paging already absorbs the average** — 1,439 MiB guest pages in a 713 MiB file
   (Test 27), `corrupt=0`. The pager hit *self-imposed* budgets first (768 MiB disk budget
   with 1,209 MiB pageable and `full=0`). Raising budgets is a shock absorber, not a plan:
   the device/storage does refuse eventually (Tests 24/25).
3. **Demand-side cuts are cheap and logged**: 20,604 blank pages stored (Test 25),
   `bda_pagetable_buffer` 128 MiB eager (handoff suggestion: lazy-commit), item-16 rule
   (optional features > 50 MiB default-off) exists but costs are unmeasured.
4. **Series X changes nothing**: the 5,120 MiB Game-mode budget is identical (PRIMARY
   sources in `../03-Memory-CPU-And-JIT/dev-mode-memory-and-system-caps.md`). GPU headroom
   helps FPS, not the wall.

## The program

### Phase 0 — Measurement loop (owner: user + agent, 1 run)
- Install latest package (`1.0.26307.1804` = docs build over the `.935` behavior baseline),
  verify version in *Manage app* (stale installs have invalidated tests before).
- Fixed regression route (above) + §7 capture fields; `loader.log.txt` + `errors.log.txt`
  preserved before relaunch; **one variable per run**.

### Phase 1 — Kill the spike (owner: agent, CI-verifiable)
Item 2 de-risked into two sub-stages — **the recovery ladder ships before fail-soft**:
- **2a (safe, no caller contract needed):** enforced reclaim ladder before every
  ≥ 16 MiB DeviceLocal allocation (`Finish → PopPendingOperations → retired-arena release →
  texture emergency reclaim → pager sweep`), 250 MiB reserve floor, arena live cap by
  **deferral to frame boundaries** (never refuse mid-draw — make room first; if still
  impossible, today's failure behavior is unchanged, so no corruption risk).
- **2b (only after 2a measured):** true split/skip fail-soft for call classes proven to
  tolerate it (readback/DMA first), with explicit caller-contract tests — per the "safe
  continuation" note; do not invent contracts for draw/dispatch.

### Phase 2 — Cut demand (owner: agent)
- Zero-page elision in the swap record path (20k blank pages/125k).
- Lazy `bda_pagetable_buffer` commit (128 MiB → on-demand).
- Steady-state texture ceiling (GC keeps a budget; emergency reclaim stops being the only
  line of defense) — measured, default-conservative.
- Item-16 rule cost table (every optional feature's real MiB, logged in-run).

### Phase 3 — Validation & ship gate (owner: user on console)
- One numbered test (#30+) per change set, matched route, honest pass/fail.
- Gate for `arena/8ac58bdb-test-project` → `main` merge + `v0.1-dev` tag: three consecutive
  green regression-route runs + ≥ 200 MiB steady-state margin + zero fault RVAs
  (`+0x3003f0/+0x26bbb7/+0x27222e/+0x272f1c`) + `corrupt=0`.
- Ship message is honest: 30 FPS / 720p / known session-length limits if any remain.

## Contingency ladder (if the wall persists after Phase 2)
L1 720p proxies + features off (already default) → L2 proactive 640×360 under pressure
(watchdog rung exists) → L3 explicit texture-cache budget → L4 documented "restart after
heavy transition" session limit for v0.x → **stop-loss**: ship the vertical with the
documented limit rather than holding the port hostage; pager/admission work continues as
v0.2. psxbox/Chiaki streaming = the "perfect today" fallback, documented, not built here.

## Explicitly not doing
- No architecture rewrite (Dozen/Liverpool stack stays).
- No Series X purchase/wait for memory reasons.
- No swap-budget inflation as the primary lever (Tests 22–25 proved it defers, not fixes).
- No `texture_reclaim_experiment=1` by default (visual corruption risk; run only as its own
  numbered experiment).
- No weakening assertions or disabling features to make CI green (standing rule).
