# Study — `XboxEmulationHub/xbox-swap` (fmalloc): fit for the Bloodborne port?

Status: STUDY COMPLETE (2026-11-09). Source read in full (355-line `fmalloc.cpp` + header +
init/deinit). Repo: GPL-3.0, C++, created 2025-11-03, last push 2025-11-04, 1 star, no hardware
evidence in-tree. Verdict: **do not link it; steal three ideas.**

## 1. What it is

`fmalloc_init(path, max_size)` reserves a placeholder window (`VirtualAlloc2FromApp`),
sub-allocates it with **o1heap** (pavel-kirienko, MIT, 423 ★, maintained), and keeps at most
`MAPFILE_MAX_LOADED_BYTES` = 512 MiB resident: a vectored exception handler ("THE SHADOW")
faults in 4 KiB pages from a sparse file (`CreateFileFromAppW` + `FILE_FLAG_NO_BUFFERING`),
evicting another page round-robin. API: `fmalloc/frealloc/ffree/fmalloc_close` (a DLL).
It is the same technique family as Test-project's `guest_swap.inc` (placeholder views +
VEH + sparse file) but aimed at **host mallocs** instead of WC_GARLIC guest pages, and
without compression, budgets, or telemetry.

## 2. Findings from the full read (function-level)

| # | Finding | Where | Why it matters |
|---|---|---|---|
| 1 | **LRU eviction is dead code** — `get_view_to_unmap()`/`views_last_swap` are never called/updated; the handler evicts `time % views.size()` (round-robin) | `ShadowExceptionHandler` | Hot pages get evicted as often as cold ones; any working set > 512 MiB thrashes 4 KiB I/O |
| 2 | **File I/O + alloc/free inside the VEH under one global `CRITICAL_SECTION`** | `ShadowExceptionHandler` | Every fault = WriteFile + VirtualFree + VirtualAlloc + ReadFile serialized across all threads; a fault storm stalls the process (the Test #22 commit-lock stall class, worse) |
| 3 | **No `ExceptionCode` check** — any SEH whose `ExceptionInformation[1]` lands in the window is "handled" and resumed | `ShadowExceptionHandler` | Masks real crashes (AVs from actual bugs inside the window range are turned into page swaps); incompatible with the port's single-winner `fatal_exception` breadcrumb contract |
| 4 | **`frealloc` memcpy overread** — copies `_Size` bytes from the old block regardless of its real size; no NULL check on `fmalloc` result | `frealloc` | Heap overread → garbage data or crash; should copy `min(old,new)` via `o1heapGetAllocatedSize` |
| 5 | **Init pre-commits all 512 MiB resident at once** and splits the window with one `VirtualFree` per 4 KiB page (≈131K–524K syscalls) | `nemory_mapping_init` | An unconditional 512 MiB resident floor is hostile to a 5,120 MiB budget battle; startup cost scales with `max_size` |
| 6 | **`UnmapViewOfFile` on `VirtualAlloc`'d pages at teardown** (wrong API; will fail) | `nemory_mapping_deinit` | Shutdown path evidently unexercised |
| 7 | Always write-back on eviction (no dirty tracking), 4 KiB granularity | handler | I/O amplification; the port's pager batches 16 KiB compressed records |
| 8 | Hard-coded 512 MiB resident cap, no budget/disk-reserve/volume policy, no telemetry, no watchdog hooks | globals | Fails item 1/3/7 integration outright |

## 3. Versus Test-project's `guest_swap.inc` (the port's own pager)

| Capability | xbox-swap | guest_swap.inc (Tests #20–29) |
|---|---|---|
| Swap target | host malloc window | WC_GARLIC guest pages only |
| Eviction policy | round-robin (LRU dead) | clock sweep w/ second-chance + fault-time pinning |
| Record format | raw 4 KiB | 16 KiB compressed records, zero-page/blank handling, pool decommit |
| Budgets/telemetry | none | disk budget growth 768→2,048 MiB, reserve, per-reason counters, breadcrumbs |
| Failure handling | `int error = GetLastError(); int debug = 0;` | fail-soft paths, watchdog escalation |
| Evidence | none in-tree | 29 hardware test logs |

The port's pager is a generation ahead. xbox-swap wins on exactly one axis: **scope** — it
swaps *host* allocations, which the port's pager does not touch.

## 3b. Step 1 BUILT (2026-11-10) — o1heap arena behind the staging pool

`youdedend/Test-project` local commit **`d31be49`** on `arena/8ac58bdb-test-project` (stacks on
`681384b` 2a; ff from `cac48ea`), delivered as `06-Boilerplates-And-Wrappers/testproject-phase1-2a/
phase1-2a-step1.bundle` + `release-2a-step1.ps1` + `release-notes-step1.md` + `bb-port-phase1-2a-step1-kit.zip`
(Drive fallback `1K_KlMhzibGEzonHw1HtGN3bmyopfW3yE`). What landed:

- **Vendored** `xbox/graphics/o1heap/{o1heap.h,o1heap.c,LICENSE}` = `pavel-kirienko/o1heap@388a73fd`
  (MIT). **Material o1heap fact found while integrating:** every allocation rounds up to a
  **power-of-two span** — `o1heap.c:390` `alloc_size = roundUpToPowerOf2(amount + O1HEAP_ALIGNMENT)`
  (same at `:555` on realloc) — so a request can consume up to 2x its bytes. Verified by probe:
  a 5 MiB arena serves 3 MiB but NOT 4 MiB (→8 MiB span). Chunk sizing therefore budgets the
  span + 50% headroom (`staging_arena.h:91`). All MiB accounting must count chunk bytes, not
  requested bytes.
- **`xbox/graphics/staging_arena.h`** (pure header): chunk = one `VideoCore::Buffer`, o1heap over
  it; `Request` (`:79`) first-fit over chunks then grow ≥32 MiB; `FreeDeferredByOffset` (`:121`)
  = the deferred-release rule; `Collect` (`:135`) frees a record only when `is_free(tick)` (the
  `scheduler.IsFree` rule, kept from the legacy path) and releases empty chunks past 120 idle
  frames. Failure to serve = caller falls through to the legacy path — the arena may
  under-deliver, never fail what the old code could serve.
- **Pool integration** (`gpu/shadps4/video_core/renderer_vulkan/vk_staging_buffer_pool.cpp`):
  arenas for HostUncached + HostCached only (`:82-96`; DeviceLocal cannot host o1heap metadata —
  VRAM is not CPU-addressable); `RequestLarge` tries the arena (`:170`); arena-aware
  `FreeDeferred` (`:233`); `Collect` in `TickFrame` (`:271`); `ResidentBytes` (`:312`) and
  `PublishStats` account arena chunks. `BB_STAGING_ARENA=0` / `staging_arena=0` restores the
  legacy path exactly (`xbox/platform/main.cpp` flag_to_env + default ini).
- **Tests**: `xbox/tests/staging_arena_test.cpp` (8 groups — tick safety, held-deferred,
  cross-size reuse 20→5+15 MiB in one chunk, alignment, growth, chunk release, fallback signal,
  offset lookup) → `staging_arena: PASS` on the build machine; `xbox.yml` row `staging_arena`
  compiles the test + `o1heap.c` for the toolchain check.

**Not yet measured** (hardware): whether freed-staging reuse actually moves the 5,055-5,116 MiB
wall / the fault RVAs — `release-notes-step1.md` defines the T13/T21-style comparison (staging
MiB, dedicated-vs-arena buffer counts, fault RVAs, T21 burst). Honest bounds: no paging, no
admission enforcement (2b), no compaction; the power-of-two span rule caps the win and must be
reported against measured chunk bytes.

### CI + release outcome (verified 2026-11-10)

Published **`xbox-alpha-1.0.26314.1455`** (pre-release, 2026-11-10T14:56:05Z, target
`9849cafba2de567f747fa2de718238544dc3f6db`) from `arena/c40c18ec-test-project` —
run [42837339701](https://github.com/youdedend/Test-project/actions/runs/42837339701) `success`
on attempt 4. Verified here via `gh api compare d31be49...9849caf` = exactly 4 commits:
`c5b15d0` (`[release]` marker + `release-notes-step1.md`), then three CI fixes — all four commit
messages carry `[release]` so the publish gate (xbox.yml:278) held at the tip:

1. **`5bce194` — the prepared 2a code's own bug** (`buffer.cpp:279-309`): my pre-alloc recovery
   block sat *after* the `#endif` of the `BB_UWP` guard yet referenced `limit` declared inside it
   → MSVC `use of undeclared identifier 'limit'` at :294/:306. Fix moved the `#endif` below the
   block and declared `const uint64_t limit = bb_uwp_app_memory_limit();` locally. Lesson pinned:
   **"host tests PASS" does not compile production .cpp** — the pure-header tests never built
   `buffer.cpp`; one CI pass is the real compile gate for integrated code.
2. **`7589edf` — MSVC has no `std::aligned_alloc`** (`staging_arena_test.cpp:35,48`): my Linux
   g++ run passed (glibc provides it); MSVC only offers aligned `new`/`_aligned_malloc`. Test
   now uses aligned `new`/`delete`; checks unchanged.
3. **`9849caf` — upstream o1heap CLZ width bug on Win64** (`o1heap.c:72-79`): upstream defines
   `O1HEAP_CLZ __builtin_clzl`; on LLP64 Windows `unsigned long` is 32-bit while `size_t` is
   64-bit, so the count was garbage → allocator log2 math corrupt → `Assertion failed:
   frag != ((void*)0), o1heap.c:416`. Linux host tests could not see it (LP64: `long==size_t`).
   Fix selects the intrinsic by width, assertion left intact:
   `#if SIZE_MAX == ULONG_MAX → __builtin_clzl / #elif SIZE_MAX == ULLONG_MAX → __builtin_clzll`.
   Anyone vendoring o1heap on Win64 needs this; worth suggesting upstream (not done — out of
   scope, do not act unasked).

Hardware validation remains outstanding (plan in `release-notes-step1.md`); the pre-release ZIP
is at https://github.com/youdedend/Test-project/releases/tag/xbox-alpha-1.0.26314.1455.

## 4. Verdict & what to steal

**Do not link `fmalloc`** (defects 1–6 make it unsafe in its current form; GPL-3.0 also forces
the combined work to GPL-3.0 — allowed since Test-project's headers are GPL-2.0-**or-later**,
but a cost with no payoff). **Steal:**

1. **The scope idea (biggest win):** a *swap-backed host arena* for the transients that item 2
   keeps fighting — `getPipelineCacheData` vectors (174 MiB class), texture CPU mirrors,
   staging/readback pools. Reuse `guest_swap.inc`'s compressed record pager + budgets +
   telemetry (don't port fmalloc's handler) with **o1heap** (MIT, safe to adopt) as the
   sub-allocator over the window. This gives 2b a real candidate: pools whose callers only
   need buffers, not contiguity guarantees across the whole run.
2. **o1heap itself** for deterministic O(1) sub-allocation inside any fixed window (candidate
   for DMA-view/staging pools; replaces ad-hoc free lists).
3. **The explicit resident-cap concept** (`MAPFILE_MAX_LOADED_BYTES`): make it a configured
   knob (`host_swap_resident_mb`) tied into the watchdog ladder, instead of a constant.

Also useful as a negative template: round-robin eviction, I/O-under-VEH, and the missing
`ExceptionCode` filter are exactly the three things the port must NOT copy.

## 5. Suggested port integration (order)

1. o1heap sub-allocator behind the staging/readback pool (no paging yet) — measurable, tiny.
2. Host-swap arena for the pipeline-cache transient, riding the existing pager records.
3. `host_swap_resident_mb` knob + watchdog rung, hardware-tested like everything else.
Steps are independent and each is a revertable commit per house rules. No claim of MiB saved
without a matched console run (standing rule).
