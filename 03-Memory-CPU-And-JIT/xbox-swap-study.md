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
