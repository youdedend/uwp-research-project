# Run 4 — `1.0.26314.2016` (`489444f`, diag-3): the crash is inside the Xbox's own D3D12 driver

Evidence: `hardware-run-2026-11-10-26314-logs/run4-2016-{loader,errors,dozen}.log`.
User, verbatim: *"talk to me like am 12 what happened and what we can do to fix it and how we can use
the knowledge of the other repos i added at the start of the chat to look for a solution"*.

## 1. What diag-3 was for, and what it delivered

The previous run ended on `module=unknown+0x23ec55` — the filter could not name the module. diag-3
fixed that, and on the first run it produced an answer:

```
1676  UNHANDLED NATIVE FAULT: code=0xc0000005 module=umd12ddi_arden.dll+0xab935
      rip=0x7ffac376b935 rsp=0xf784ffef60 addr=0x10
1680  UNHANDLED FAULT CONTEXT: addr is in not mapped, protect=0x1 state=0x10000 type=0x0
1677  UWP thread op: tid 2564 in 'recording Vulkan command' (0x0, 0x7ff675bf0f18) for 175 ms
1678  UWP thread op: tid 3248 in 'processing a PM4 submission' (0x0, 0x9) for 773 ms
1679  UWP thread draw: tid 6820 graphics #107768 marker=indexed
```

Read literally:

- **`umd12ddi_arden.dll` is Microsoft's Xbox D3D12 user-mode driver** ("User Mode Driver for
  Direct3D 12"), not our code and not Mesa's translator.
- `addr=0x10` with `state=0x10000` (MEM_FREE) and `protect=0x1` (no access) — the code read
  through a **near-NULL pointer** (`[0x10]`, i.e. NULL + 0x10). That is a member read on an object
  the driver failed to create or already released, not a data-corruption address.
- It died on the thread **recording Vulkan commands** (175 ms into the current command), while the
  PM4 processor was 773 ms into its submission and the game's render thread was on graphics draw
  **#107,768**. So: the game was ~50 s into the run, at 1,463 presents (world load in progress),
  and our translator was submitting work to the driver when the driver crashed.

Progress by build, all measured on the same route:

| build | furthest point | where it died |
|---|---|---|
| `26314.1455` | character-creation transition, 1,225 presents | stale image in `vulkan_dzn.dll` (`+0x1fd79`) |
| `26314.1903` | 2,176 presents | same stale image (`+0x1fd79`) |
| `26314.1946` (diag-2) | character visible+created, 2,326 presents | private-memory fault, module unknown |
| **`26314.2016` (diag-3)** | **1,463 presents, world load under way** | **`umd12ddi_arden.dll` NULL+0x10** |

diag-2's fault is gone in the last two runs (four consecutive runs had it before). This run is
shorter in presents because it loads faster with a warm cache; the wall is the same phase.

## 2. What the other repos say — and it is not "nothing"

Three pieces of evidence, each with its source:

**(a) Dozen crashes inside the D3D12 user-mode driver on Xbox — known, not ours.**
- `jobucaldas/xboxnative` PR #116 (`feat(play): Vulkan runs for real — Mesa's dzn as the packaged
  ICD`) ships **four dzn patches just to make it survive on the console**, including
  *"0006 dzn's meta cleanup is idempotent, so a failed device creation does not Release() through a
  freed vtable on the second cleanup pass"* — a NULL/garbage-pointer crash on a device the driver
  never created, the same shape as ours. It also notes *"console acceptance of unsigned DXIL is
  still unverified"*.
- `boykopovar/AnyPS5` issue #3255: *"The crashes are 0xc0000005, right after Vulkan surface
  created, with the faulting thread in a D3D12 user-mode driver"* — with `VK_LOADER_DRIVERS_DISABLE`
  as the workaround.
- `libretro/dolphin` issue #207: a UWP Xbox crash whose stack is `umd12ddi_arden!SetDebugBits+0x20510`
  ← `D3D12Core!D3D12GetInterface` ← `d3d11on12!OpenAdapter`. **The same DLL, from a project that has
  nothing to do with ours.**

So: dzn on the Xbox hits the OS driver's own limits, and the fix in every case above was **not**
"patch the driver", it was *avoid the driver path that trips*.

**(b) Our dzn pin is already the newest.** `MESA_COMMIT=a76cd3caa23f` is the tip of
`Cosmo/mesa_ai_slop_version` branch `dozen-perf` (2026-10-21, "dzn: Skip the buffer descriptor cache
for buffers whose ranges change"); `dozen-update` is older (`82804960`, 2026-10-18). There is nothing
to update to — so "bump Mesa" is not the lever. (Verified with `gh api` today.)

**(c) The fork has runtime switches we are not using.** `1f8f581d43` "dzn: Add switches that hide
D3D12 capabilities for testing" adds `DZN_DEBUG` options `nobindless`, `experimental`, `multiview`,
`no16bit`, `nostencilref`; `cc9399eb37` adds `DZN_DEBUG=d3d12`, which *"Log D3D12 debug layer
errors"*. In this run `dozen.log` is 150 bytes — the two conformancy warnings — i.e. **the dzn debug
layer was OFF**, so the driver said nothing before it died. The port already forwards `DZN_*`,
`MESA_*` and `BB_*` keys from `LocalState\graphics-debug.txt` into the environment
(`xbox/platform/main.cpp:2412-2415`), so switching these on needs **no build**.

## 3. The decision tree this produces

1. **`DZN_DEBUG=d3d12` in `graphics-debug.txt`** (no build, one file). The D3D12 debug layer
   reports the *invalid* call before the fault instead of after it. This is the single highest-value
   next step, and it is free.
2. **`DZN_DEBUG=nobindless,no16bit,nostencilref`** in the same file: hide three D3D12 capabilities
   dzn advertises. If the driver's NULL comes from a feature the console driver pretends to support
   (bindless descriptors, 16-bit ops, stencil reference), the crash moves or disappears and we know
   which capability to report to the driver instead of shipping work it cannot take.
3. **The same route with `swap_file=off`** (`bbport.ini`): separates "the pager handed back a page
   the driver still had" from "the driver's own object is broken". One run, decisive.
4. Only if 1-3 leave it ambiguous: instrument around the failing submission in our own code (log the
   descriptor set / command being recorded when the fault thread is in `recording Vulkan command`).
   That is a build; the three above are not, so they go first.

## 4. What we do NOT claim

- Not that the driver bug is understood. We know the module, the thread, the instruction's data
  dependency (`[0x10]`) and that a sibling project had to patch dzn to stop the same class of crash.
- Not that `nobindless`/`no16bit` are relevant — they are cheap experiments, and the debug layer in
  step 1 is what would justify them.
- Not that this is our regression: unlike the `0x1fd79` fault, nothing in our history dates this one.
  The first three builds never got far enough to reach it, which is the honest reading of the table
  in §1.
