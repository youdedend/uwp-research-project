# Run 6 — `1.0.26314.2323` (`f26348e`, diag-5): layer off, a new record, and a new dzn fault

Evidence: `hardware-run-2026-11-10-26314-logs/run6-2323-loader.log` (267,084 B, 2,210 lines),
`errors-6.log` (19,700 B, 76 lines), `dozen.log` (**150 bytes**). User, verbatim: *"game didnt crash
just stuck and its only 6fps"* (that sentence was written about the run before this one; the files here
are the layer-off run that followed).

## 1. diag-5 was published by another session and is working

`f26348e` is my `c5a784c` plus a release-notes commit, on `arena/c40c18ec-test-project`; the build is
`1.0.26314.2323`. Both diagnostics fire in this log:

- **`base=` appears on a fault line for the first time in the program's history.** The third crash we
  could not place is now placed without arithmetic:
  `module=vulkan_dzn.dll+0x20810 base=0x7ffaac820000 rip=0x7ffaac840810`.
- **The truncated-stream diagnostic printed the dwords** (§4).

That closes the loop on the diag-5 kit: the work was needed, it was applied, and it immediately paid
for itself.

## 2. The debug layer was off, and the result is the best the project has seen

`dozen.log` is **150 bytes** — only the two "not a conformant Vulkan implementation" warnings. Against
run 5's 8.7 MB and the layer-on run's 14.5 MB, this settles it: **the layer was off for this run.**

| | layer on (run 5 / 2112) | **layer off (2323)** |
|---|---|---|
| presents | 1,764 | **2,577** |
| presents per second after warm-up | — | **~25 fps** (2,577 over ~102 s) |
| reached | stall → fault | stall → fault, but 813 presents later |

So: turning the layer off bought back roughly 4× the frame rate over the layer-on runs and **the
furthest point this project has ever reached**. The 6 fps the user reported was the debug layer, as
predicted; the number to quote now is ~25 fps.

What it did **not** do: prevent the stall, and prevent a fault. Those are separate from the layer.

## 3. The fault is a new one, in dzn, with a reserve-state address

```
UNHANDLED NATIVE FAULT: code=0xc0000005 module=vulkan_dzn.dll+0x20810 base=0x7ffaac820000
                       rip=0x7ffaac840810 rsp=0xcd2d3ffa08 addr=0x23fb16ed5bc
UNHANDLED FAULT CONTEXT: addr is in a private allocation, protect=0x0 state=0x2000 type=0x20000
```

- `state=0x2000` is `MEM_RESERVE` and `protect=0x0` is `PAGE_NOACCESS`: the address *belongs to the
  process* (it is inside a reservation we made) but has never been committed. So this is not
  use-after-free (which would read `MEM_FREE`, `type=0`) — it is a **read/write to a page inside a
  reservation that was never committed**, i.e. a guest-memory address whose page was not backed at
  that moment.
- `addr=0x23FB16ED5BC` is **not** in guest space: the emulator's guest address space is 40 bits
  (`ADDRESS_SPACE_BITS = 40`, `buffer_cache.h:42`), i.e. up to `0xFFFFFFFFFF`, and this address is
  1,279 GiB past that — about 2.5 TiB. So it is a full 64-bit address that happens to be reserved in
  our own process, and the most likely origin is a **guest 32-bit pointer widened wrongly** or a host
  pointer with garbage in the top bits, not a plain guest read. The faulting thread was **`recording
  Vulkan command`** (1,057 ms in that op), with `tid 4108` behind it in *'processing a PM4 submission'*
  for 2,731 ms.
- Crash history, now readable at a glance:

  | build | fault | `addr` |
  |---|---|---|
  | 1455 / 1903 | `vulkan_dzn.dll+0x1fd79` | `0x148` |
  | 2112 | `D3D12Core.dll+0x240d96` | `0xFFFFFFFF000001B8` (= slot `-1`) |
  | **2323** | **`vulkan_dzn.dll+0x20810`** | **`0x23fb16ed5bc`, reserved-not-committed** |

  Three different signatures in three builds, and the latest is *not* the slot `-1` bug — that one did
  not fire here. Every build moves the crash, which means each one gets past the last obstacle and
  meets the next. That is progress, but it is not yet a fix.

## 4. diag-5's own line, read properly

```
liverpool.cpp:110 : truncated stream: 1 dwords, overrun by 1; first [c0001000] last [c0001000]
liverpool.cpp:70  : packet length exceeds remaining submission size. Packet dword count=2,
                    remaining submission dwords=1
```

`0xC0001000` is a Type-3 header: type `3`, **count `0`**, opcode `0x1000`. The decoder's `NumWords()+1`
is `1`, so it consumed the header, and the *next* iteration asked for offset `2` with one dword left.
Two readings fit and the log cannot separate them: either the header genuinely carries `count=0` and a
second packet never arrived, or `0x1000` is an opcode this decoder does not model and the count field
is garbage. Either way it is **one dword at a stream end**, it was present in the run that reached
2,577 presents, and it is therefore almost certainly not the crash — it is the tail of a stream that
was already being abandoned.

## 5. The proxy accumulation: what is true and what I got wrong

The stall is preceded by this block, and it looks alarming at first read:

```
Camera motion: scene render size 1920x1080
UWP resolution: native target 1920x1080 allocation=8704 KiB retained; proxy 1280x720 … live proxies=1 … 7
UWP dense GPU arena: merge #7 … merge #8 …   (arena live 800 MiB, ring 272 MiB in 17 blocks)
```

**Correction, before this propagates:** the `live proxies=1…7` numbers are a *running total for the
whole run*, not seven allocations in one second. Those lines carry **no timestamp**, so the earlier
reading ("seven proxies inside the same second") was an inference from line order and is withdrawn.
The real figures: `SetSize` ran **once** (`1920x1080 -> 1280x720`, releasing 0 existing proxies), and
the entire run created **7 proxies totalling 58 MiB**. For a 4.5 GiB budget that is not a leak and not
a plausible cause of a stall. The design is sound: `entries` is keyed by `(image_uid, mip)`, cleared
wholesale on a size change, and `recent` is only a lookup cache of raw pointers.

So the honest position on the stall is: **the last thing logged before it is a pair of arena merges
(`merge #7`, `merge #8`, copying 32 MiB each) with `ring=272 MiB in 17 blocks`, and that is where the
investigation should look — not at the proxies.** Merges are synchronous copies on the recording
thread (already instrumented as `UWP thread op: … dense-arena merge copy`), and two of them plus a
272 MiB ring at the exact moment presents stop is a much better fit for "the recording thread is busy
for 10 s" than 58 MiB of proxies ever was.

The watchdog again **did not take its 10 s exit** even though presents sat frozen for ~30 s
(`t=74 s → 102 s`), so the exit step remains broken and still costs a full stall window per run.

## 6. Next

1. **Trap the bad pointer at its source, not at the fault.** The address is 1,279 GiB outside guest
   space, so the interesting question is *where it was formed*, not which page it hit. One build with a
   check in the two paths that widen a guest address into a host pointer (the buffer cache's
   `ObtainBuffer` range check and the texture/presenter pointer hand-off), printing the guest address,
   the resulting host address and the caller, would name it in one run. Cheaper than chasing the page.
2. **Watch the arena merges at the stall.** `merge #7` and `merge #8` are the last lines before
   presents stop, each a synchronous 32 MiB copy recorded on the same thread that then faults. The
   instrumented span (`bbgpu_thread_op("dense-arena merge copy")`) already measures it — the next run
   should report that span in the stall dump (it is collected but the stall block prints thread names,
   not ops). If the merge copy is where the 10 s goes, the fix is to stop merging at that moment, which
   is a policy change we can make safely without touching rendering.
3. **Log the watchdog's exit gate.** Two runs in a row have now shown the 10 s exit not firing. One
   line saying which condition failed removes a permanent blind spot.

## 7. The user's answer closes one thread: the picture is correct

Asked directly whether the image looked right at ~25 fps, the user answered **"all thing correct"**.
That is the answer the 24,409 debug-layer messages were owed, and it settles their status:

- The buffer-state defect (we emit one global `MemoryBarrier2` and never a `VkBufferMemoryBarrier2`,
  so dzn transitions every buffer itself on first use) **does not corrupt what is drawn.** Two hot
  vertex buffers, thousands of transitions per second, and the image is right.
- Therefore it is **hygiene, not a bug to chase**: worth fixing for the log noise and for the driver's
  own state machine, worth *not* spending a build on while there is a 10 s stall and a fault.
- It also means the 6 fps → 25 fps improvement was real frame rate on a correctly rendered scene, not
  a game limping along with broken output. The cheapest lever we have found so far was a settings
  edit, and it produced the best-looking, fastest run in the program's history.
