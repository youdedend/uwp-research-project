# Run 3 — `1.0.26314.1946` (`fef8bc4f`, diag-2): the dzn crash is gone, a stall took its place

Evidence: `hardware-run-2026-11-10-26314-logs/run3-1946-loader.log` (2,650 lines),
`run3-1946-errors.log`, `run3-1946-dozen.log`. User, verbatim: *"now i can see character but crash
when gameplay suppose to start"*.

## 1. What the fix did

The regression identified in `regression-watchdog-image-reclaim.md` is **gone**:

- **No `vulkan_dzn.dll+0x1fd79` fault in the entire run.** That signature appeared in four
  consecutive runs of three earlier builds (`26314.1455` twice, `26314.1903`), and this is the
  first build without it. This is a reproduction-based statement, not an inference: the same route,
  the same phase, four times before.
- The fix's own log line fired: `run3-1946-loader.log:954`
  `Texture cache: render-thread reclaim of the watchdog's request freed 76 MiB of 112 MiB asked
  (76 MiB in total; running it here is diag-2)`.
- The step-1 staging row reads real numbers now (`ring=272 MiB in 17 block(s), resident=272 MiB`,
  line 2263 area) where diag-1 reported `0 MiB` throughout. Q1/Q2 (arena vs legacy staging) can be
  measured on the next run; on this one the arena held nothing while 17 ring blocks held 272 MiB.

Progress against the user's own milestones:

| build | furthest point |
|---|---|
| `26314.1455` | freeze in the character-creation → world-load transition, 1,225 presents, dzn fault |
| `26314.1903` | 2,176 presents, dzn fault ~1 s after the watchdog's degrade step |
| **`26314.1946`** | **character visible and creation completed, 2,326 presents, world load begins, NO dzn fault** |

## 2. What stopped it

```
... t=68s presents=2325 -> 2326 and no further present for the rest of the run
fences: submitted=4649 completed=4648 outstanding=1     (fence age 39,961 ms = 40 s)
UWP thread op: tid 5924 in 'recording Vulkan commands' for 785 ms / 2848 ms
UWP thread op: tid 1028 in 'processing a PM4 submission' for 1262 ms / 3325 ms
then, 0.6 s after "recovery: degraded":
UNHANDLED NATIVE FAULT: code=0xc0000005 module=unknown+0x23ec55 rip=0x7ffac2edec55
                       rsp=0x899bff350 addr=0x1429f5fed70
```

Notes that matter for the next build:

- The fault address `0x1429_f5fed70` is **private memory, not image space** — the process's image
  addresses in the same log are `0x7ffa…` and `0x7ffb…`. So this is not another stale-Vulkan-object
  crash of the `dzn+0x1fd79` kind; it is a read/write through a pointer into heap or guest memory.
- The run paged heavily: `out=1580 in=256 disk=747 views=64 MiB; checks=17685 corrupt=0 window
  evictions=12220`, `copy-out=113486 copy-in=17763`, `swap keeps out of RAM: 1020 MiB of guest
  pages`. A read from a guest address that the pager took away would fault exactly like this.
- Both `26314` builds faulted within ~1 s of the watchdog's **degrade** step (`recovery: degraded`
  breadcrumb in `1903` and `1946`). The degrade step only stores settings (upscaler/frame-gen off,
  preset down a notch) and posts a breadcrumb — it does not touch GPU objects — so this is more
  likely the moment the game *consumed* the changed state than the step itself.
- The watchdog's own report is healthy throughout: `swap write failures=0`, `copy-in (failed 0)`,
  `corrupt=0`, no ladder step other than one `release` that freed 0 MiB because the images had
  already been reclaimed on the render thread.

## 3. Why the report cannot say more, and what diag-3 adds

`module=unknown` because the fault filter named only three modules by handle; `0x23ec55` is an
offset into a module it did not know. diag-3 (`e2de023`) fixes exactly that and nothing else about
the renderer:

1. `ModuleNameForAddress()` — enumerates the process's modules (resolved through the loader, since
   psapi is not in the UWP API partition) and names the module owning the faulting rip. A new
   `UNHANDLED FAULT CONTEXT` line names the module or private allocation owning the **fault
   address**, with its protect/state/type, and the full thread report is taken at the fault.
2. `CommandChunk::Execute` tags the command index + vtable pointer (one tag per second, so no
   per-command cost) and `DrawRecord`/`DispatchRecord` register what they draw, so a stall names
   the command and the draw instead of only the thread.
3. A fence stuck for more than 3 s now dumps the stall report on its own. In this run 40 s of dead
   fence produced one dump only because the presenter had also stopped, and it was luck.

## 4. Two experiments the next run can carry (user's choice, one build each)

- `swap_file=off` in `bbport.ini`: the same route with the pager inactive. If the fault disappears,
  the pager's paged-out guest pages are implicated; if it stays, the pointer itself is bad.
- `DZN_DEBUG=d3d12` in `graphics-debug.txt`: dzn's debug layer into `dozen.log` (150 bytes in this
  run = only the conformancy warnings, i.e. the flag was not set).

Neither is required for the diag-3 build to be useful: on its own it will name the module and the
command.
