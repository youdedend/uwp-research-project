# Regression: the watchdog frees texture-cache images off the render thread (found 2026-11-10)

Evidence base: run 2 of `xbox-alpha-1.0.26314.1903` (`f531b31`, the published diag-1 build).
Logs committed beside this file in `hardware-run-2026-11-10-26314-logs/` as
`run2-1903-loader.log`, `run2-1903-errors.log`, `run2-1903-dozen.log`, `run2-1903-bbport.ini.txt`.
Trigger, verbatim from the user: *"i didnt have this problem with earler versions"*.

## 1. What the user saw

The game got further than ever — 2,176 presents (the previous build stalled at 1,225) — through
the intro, character creation and the start of the world load, then froze. The fault is the same
one decoded on 2026-11-10 from a minidump:

```
UNHANDLED NATIVE FAULT: code=0xc0000005 module=vulkan_dzn.dll+0x1fd79 rip=0x7ffbfb3cfd79
                       rsp=0x27fd9ff110 addr=0x148          (run2-1903-loader.log:1466)
UNHANDLED NATIVE FAULT: code=0xc0000005 module=vulkan_dzn.dll+0x1fd79 ... addr=0x150
                                                             (loader-2026_11_10-2.log.txt:2003)
```

`0x1fd79` is `mov rcx, [rax+0x70]` inside `dzn_image_get_copy_loc()` (`dzn_image.c:438-444`),
reading `image->vk.base.device->physical`. `addr` 0x150 ⇒ rax = 0xE0; `addr` 0x148 ⇒ rax = 0xD8.
Both are garbage, i.e. a **stale/freed `dzn_image`** reached the image-copy builder. The decode
and the Mesa pins are in `hardware-run-2026-11-10-26314.md` ("### DECODED").

## 2. Ordering, from the log (verbatim lines)

```
1067  GPU: copy layer mismatch skip #1 (poisoned pairs: 0)
1068  GPU: copy layer mismatch: source D16Unorm 1x1x1 layers=1 addr=0x10d1d50000 | destination
      D16Unorm 1x1x1 layers=2 addr=0x10d1d50000; skipping the copy
      Texture cache: free id=94 uid=94 by=other guest=0x10d1d50000 size=65536 ... deferred=1
      ... (skips #2-#5, ids 95-98, same guest address)
1146  UWP watchdog: step release (arenas, staging, images) started
      (headroom 327 MiB, usage 4792/5120 MiB, presents 2176, stuck 0 ms)
1235  Texture cache: emergency reclaim freed 69 MiB of the 72 MiB asked for; seen=198
      too recent=0 gpu-written=118 bound/target=1 no backing=5 (gc_tick=2142)
1237  UWP watchdog: step release (arenas, staging, images) freed 69 MiB in 257 ms
1428  UWP thread op: tid 5944 in 'recording Vulkan commands' (0x14c, 0x0) for 2249 ms
1466  UNHANDLED NATIVE FAULT ...
```

The depth textures being re-created at one guest address (`0x10d1d50000`, layers 1→2→3→4→5→6,
`deferred=1`) are the ones the image-to-image copy path walks, and the reclaim took 69 MiB of
images 257 ms before the render thread was seen stuck in command recording.

## 3. The regression, dated by tag

`git log -S "bbgpu_uwp_recovery_step" -- gpu/shim/bbgpu.cpp` → `abb3d5c` "build 3: merge
accounting, fail-soft allocation, recovery watchdog, feature budgets". Checking each published tag
for `EmergencyReclaim` in `gpu/shim/bbgpu.cpp`:

| tag | published | watchdog reclaims images? |
|---|---|---|
| `xbox-alpha-1.0.26301.1156` | 2026-10-28 | **no** |
| `xbox-alpha-1.0.26302.0802` | 2026-10-29 | **yes** |
| `xbox-alpha-1.0.26302.0935` | 2026-10-29 | yes |
| `xbox-alpha-1.0.26307.1804` | 2026-11-03 | yes |
| `xbox-alpha-1.0.26314.1455` | 2026-11-10 | yes |
| `xbox-alpha-1.0.26314.1903` | 2026-11-10 | yes |

So "earlier versions" is exactly right, and the boundary is `26302.0802`.

## 4. Why it is unsafe

- Step 1 runs in the watchdog's **detached worker thread**: `run_watchdog_step` is called from the
  worker's loop at `xbox/platform/main.cpp:2941`, inside the `std::thread([queue] { ... })` body.
- `EmergencyReclaim` (`texture_cache.h:221`) takes `std::scoped_lock lock{mutex}`.
- The renderer's index paths do **not** take it: `GetImage` (`texture_cache.h:323-333`) reads
  `slot_images[id]` and returns a reference; the binding walks and the copy recording likewise hold
  raw `Image`/`ImageId` across the call. The file's own comment on the next member says the
  collected-image list is "same thread as the rasterizer" — the ownership model is single-threaded.
- Therefore the worker can erase a slot the render thread still refers to, and the resulting
  freed `vma`/`dzn_image` is what `dzn_image_get_copy_loc` dereferences.
- The file already applied the opposite rule for staging, one line above the image reclaim:
  *"Staging's vectors are renderer-owned. Request its normal idle trim there rather than mutating
  them from the watchdog worker while a producer holds a StagingBufferRef."* The image path was
  the exception.

## 5. The fix (`8cb181c`)

- `gpu/shadps4/video_core/renderer_vulkan/texture_cache_reclaim_request.h` — `BbUwp::ReclaimRequest`
  (atomics; coalesces to the largest pending budget; `0` ⇒ 32 MiB default; `FreedTotal()` for the
  report).
- `bbgpu_uwp_recovery_step` step 1 calls `RequestEmergencyReclaim(ask)` and reports
  `images asked N MiB - deferred to the render thread`.
- `Rasterizer::OnSubmit()` (`vk_rasterizer.cpp`, `#ifdef BB_UWP`) calls `RunPendingReclaim()`, which
  performs `EmergencyReclaim` and prints
  `Texture cache: render-thread reclaim of the watchdog's request freed N MiB of M MiB asked`.
- Reclaim still happens during a stall (OnSubmit runs whenever a submission is handed over), so the
  memory ladder keeps its teeth.

## 6. Limits of this claim

Not proven: that this is the *only* route to a stale image; that the 69 MiB reclaim specifically
erased the images in the mismatch skips (the addresses match, the ownership does not). Proven: the
same fault signature in both 26314 builds, the reclaim running outside the render thread since
`26302.0802`, and no build before that having a watchdog image reclaim. The hardware run on
`8cb181c` decides it.

## 7. Side findings from the same log (both fixed in this tip)

- diag-1's `staging:` row read `arena=0 MiB in 0 chunk(s) | dedicated=0 MiB in 0 buffer(s)` at every
  sample, including through a 2.4 GiB burst (line 1196: `usage=4774/5120 presents=2176`). Cause:
  `GetStats()` counted the arena and large caches but never the ring blocks. Fixed (ring/resident
  columns added); the step-1 Q1/Q2 split still needs one more run.
- diag-1's wedge tags never appeared: `bbgpu_thread_op_dump()` was wired only to the stall dump
  (`main.cpp:2877`, `:3022`), never to the native-fault filter. The only tag in the whole log is
  `recording Vulkan commands`, set by the rasterizer itself. Fixed: the fault filter dumps it now.
- `UWP thread op: ... 'recording Vulkan commands' for 2249 ms` — the render thread was still alive
  and recording 2.2 s into the stall: the freeze was the fault, not a deadlock.
- Swap/pager remained healthy: `corrupt=0`, `write failures=0`, no ladder step besides the release.
- `dozen.log` contains only the two conformancy warnings — the dzn debug layer was not enabled in
  this run, so no `DZN_DEBUG=d3d12` detail exists for the fault.
