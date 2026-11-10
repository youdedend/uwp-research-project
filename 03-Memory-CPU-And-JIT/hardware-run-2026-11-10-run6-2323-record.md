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
- `addr=0x23fb16ed5bc` is in the guest address range (the log's other guest pointers are
  `0x10…`/`0x1…`; this one is just outside every guest image the emulator maps), and `VirtualQuery`
  says the page is inside a reservation we own. The faulting thread was **`recording Vulkan
  command`** (1,057 ms in that op), with `tid 4108` behind it in *'processing a PM4 submission'* for
  2,731 ms.
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

## 5. Two stalls, one shape, and it is ours

Both the 2112 run and this one stall at the same place, and the log names it:

```
Camera motion: scene render size 1920x1080
UWP resolution: native target 1920x1080 allocation=8704 KiB retained; proxy 1280x720 … live proxies=1  total=3904 KiB
                                                                                          live proxies=2  total=7808 KiB
                                                                                          …
                                                                                          live proxies=7  total=32064 KiB
UWP dense GPU arena: merge #7 … merge #8 …   (arena live 800 MiB, ring 272 MiB in 17 blocks)
```

Seven resolution proxies allocate inside the same second, each **retaining** an 8,704 KiB native
target, while arenas merge and the staging ring grows to 272 MiB. Presents stop at that moment in both
runs. This is our proxy/presenter path, it is reproducible across builds, and it is a better target
than any driver theory: it is the last thing that happens before the stall, and it is code we own.

The watchdog again **did not take its 10 s exit** even though presents sat frozen for ~30 s
(`t=74 s → 102 s`), so the exit step remains broken and still costs a full stall window per run.

## 6. Next

1. **Find the uncommitted guest read.** The fault is a read into a `MEM_RESERVE` page from the
   recording thread. The guest pager commits pages on touch; a read that reaches a page the pager has
   reserved but not committed means either a missing commit in the fault path or a speculative reader
   (`BbToggle::FaultWindow` / the draw-preparation workers) reading outside what it asked for. The
   address and the toggles to try (`BB_FAULT_WINDOW=0`, and the draw-preparation toggle) are all in
   the log's reach now.
2. **Bound the resolution-proxy growth.** Seven retained 8.5 MiB natives plus their proxies inside one
   second is not a requirement of anything; the presenter should reuse one. This is the single
   cheapest change that could remove the stall, and it is testable in a host test.
3. **Log the watchdog's exit gate.** Two runs in a row have now shown the 10 s exit not firing. One
   line saying which condition failed removes a permanent blind spot.
