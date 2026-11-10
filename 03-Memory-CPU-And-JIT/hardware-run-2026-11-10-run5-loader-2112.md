# Run 5's loader log arrived — and the crash signature is not any of the three we knew

Evidence: `hardware-run-2026-11-10-26314-logs/run5-2112-loader.log` (358,511 B, 3,151 lines,
md5 `4c02377a…`). This is the file that was missing from the first run-5 upload; it is
**`1.0.26314.2112` `fa07c6333a51`**, the migration build, and the fourth run of the same session
(11:10 → 1903, 11:48 → 1946, 12:25 → 2016, **13:17 → 2112**).

## 1. Correction to the milestone table

| build | presents | fault | module |
|---|---|---|---|
| `1455` | 1,225 | `0xc0000005` | `vulkan_dzn.dll+0x1fd79`, `addr=0x148` |
| `1903` | 2,176 | `0xc0000005` | `vulkan_dzn.dll+0x1fd79`, `addr=0x148` |
| `1946` | 2,326 | `0xc0000005` | `module=unknown+0x23ec55`, `addr=0x1429f5fed70` |
| `2016` | 1,464 | `0xc0000005` | `umd12ddi_arden.dll+0xab935`, `addr=0x10` |
| **`2112`** | **1,764** | `0xc0000005` | **`D3D12Core.dll+0x240d96`, `addr=0xffffffff000001b8`** |

**`1946`'s `module=unknown` was `D3D12Core.dll` all along.** This is arithmetic, not a guess: `2112`'s
line gives `rip=0x7ffac2ee0d96` at `+0x240d96`, so that module is based at `0x7ffac2ca0000`; `1946`'s
`rip=0x7ffac2edec55` minus that base is exactly `0x23ec55`. Both runs faulted **inside D3D12Core, 8,513
bytes apart**, i.e. around the same call. diag-3's whole reason for existing (name the module) has now
paid off twice: it means `1946` and `2112` are one bug, and the window is ~8 KiB of D3D12Core.

An earlier reading of this run's `dozen.log` (the debug-layer-only file) suggested "all state errors,
no fatal line, probably no crash". The loader log kills that: **the run did crash**, and `dozen.log`
simply does not receive fault text (it is the D3D12 debug channel, not the app's stdout).

## 2. What the run actually did

- `UWP settings: added dzn_debug to bbport.ini (settings_rev 3 -> 4)` — the **revision-3 → 4 migration
  ran on this build** and printed the exact line diag-4b added. That is the third independent
  confirmation, and the first from a build log rather than from the ini file.
- No `dzn_debug=` value is echoed anywhere in `loader.log`, so the ini cannot be cross-checked from the
  log — the debug layer's presence is established only by `dozen.log` being 8.7 MB.
- Fence health is **good** through 1,750 presents: `submitted=3456 completed=3455 outstanding=1
  age=0 ms`. Then presents stop at **1,764** (`t=55 s`).
- `UWP STALL DETECTED (presents stuck at 1764 for 10 s, gpu fence age 2174 ms)`.
- The watchdog fires **all three** steps once, and they all fail to help: `release` freed 0 MiB,
  `pager sweep` freed 32 MiB, `degrade` 0 MiB — at `headroom 667 MiB usage 4452/5120`. **There was no
  memory pressure.** This is the first run in the program where the stall is not memory-driven.
- The thread report at the stall is the useful part: `GXRenderThread … running`, `MOMainThread …
  running`, `main … running`, while the cloth/character worker threads (`CSClothThread0-5`,
  `CSChrThread0-5`, `CSChrBackInitialize1`, `FaceGenMan`, `SpClothVertexUpdate`) all wait 2–4 s on
  conditions from the same caller. The render thread is alive and busy; the game is waiting on work
  that never completes.
- Thread-time confirms it: at the stall `tid 5392 36844 ms (62.8%)`, `GpuCommandProcessor 12234 ms
  (20.9%)`, `bb:VkRecorder 7000 ms (11.9%)`, `bb:DrawRec 6719 ms (11.5%)`. Recording commands is
  expensive and the PM4 submission thread is a fifth of a core — but neither is *stuck* in the report.
- Then, **~45 s after the stall** (last telemetry: `fence age=46678 ms`), one fault:
  `D3D12Core.dll+0x240d96 addr=0xffffffff000001b8`, "addr is not mapped", on a thread tagged
  **`recording Vulkan command`** (155 ms in that op). Nearby, `tid 1480` had been in *'processing a PM4
  submission' for 9,427 ms*.

The `addr=0xffffffff000001b8` is the most diagnostic number in the log: the low half is `0x1b8`, the
high half is `0xffffffff`. A 64-bit value whose upper 32 bits are all ones and whose lower 32 are a
small offset is a **32-bit quantity that was sign-extended**, or a pointer relative to `-1`. D3D12Core
indexed off a null/-1 base into a field at `+0x1b8`.

Note what the watchdog's own rule says: `stuck 3 s degrades / 10 s exits`. **It never exited** — no
`watchdog: exit` line exists — even though presents sat frozen for ~45 s. That is a separate bug worth
a line in the next build (the exit step is either gated on something that never becomes true, or the
exit path is itself blocked).

## 3. Where the engine thinks it is

`Runtime: save data 'SPRJ0005' mounted at /savedata0 (existing)` appears three times, and the stall
window is full of asset activity: `Core.Res.CacheableFileLoader` waiting on
`/app0/dvdroot_ps4/obj/o240089.o`, seven `UWP dense GPU arena` allocations growing `live 576 → 768
MiB` inside one second, and the resolution block switching `scene render size 1920x1080` with native
targets **retained** plus accumulating proxies (`live proxies=1 … 7`, `total=32064 KiB`).

Read together: at 1,764 presents the engine begins a **new area/asset load while the render thread is
still presenting the old one**, allocates seven arenas and seven proxies inside a second, then stops
presenting. That is the shape of an asset-load stall that ends in a driver call with a bad index — not
of the memory-pressure stalls diag-1/2/3 were built for.

## 4. What this changes about the plan

- **diag-5 as packaged is still correct** and now more valuable: it prints `base=0x…` on every fault
  line, which is exactly the arithmetic in §1 that had to be done by hand here. It also names
  truncated streams. Ship it.
- **The buffer-state (barrier) thread is not the crash.** It stays a real defect, but nothing here
  points at it, and the debug layer already gave everything it had. Do not spend the next build on it.
- **The next build's target is D3D12Core around `+0x240d96`.** Two cheap next steps, in order:
  1. `dzn_debug=d3d12,nobindless` as an A/B. `nobindless` is a documented dzn option
     (`src/microsoft/vulkan/dzn_device.c:204`, `DZN_DEBUG_NO_BINDLESS`) and we *do* enable
     `bufferDeviceAddress` (`vk_instance.cpp:683`) plus descriptor indexing, so dzn's bindless path is
     active on the console. A D3D12Core index fault with `0xffffffff` in the high half is consistent
     with a descriptor/heap index computed through that path. One run decides it.
  2. If that changes nothing, the asset-load stall is the next target: the resolution-proxy
     accumulation (`live proxies=1…7` in a second, each keeping a retained native target) and the
     seven arenas are both ours, and both grow exactly when the render thread is supposed to be
     presenting.
- **The missing watchdog exit** is a two-line diagnostic (log which gate failed) and belongs in the
  same build; without it, every future stall costs 45 s of log before anything says why.
