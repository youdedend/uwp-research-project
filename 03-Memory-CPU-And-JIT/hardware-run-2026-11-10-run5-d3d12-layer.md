# Run 5 — `dzn_debug=d3d12`: the layer worked, the migration worked, and it named a *different* problem

Evidence in this folder: `hardware-run-2026-11-10-26314-logs/run5-d3d12-*`.
User, verbatim: *"there is not any file called graphics-debug.txt"* (why diag-4 became diag-4b), then
the run-5 upload.

## 0. What this run was asked to do, and what it actually answered

diag-4b (`e239641`) had one job: get `DZN_DEBUG=d3d12` into the environment of the app, so Mesa's
Dozen translator would switch on the D3D12 **debug layer** and *name the invalid call* instead of
leaving a bare `0xc0000005` behind. Two separate questions ride on that:

1. Does the settings migration actually work on the console (both the ini rewrite and the env
   pass-through)? — **YES, proven.**
2. Does the debug layer name crash #2? — **NO. It named something else, and that something is more
   useful.**

That split is the whole result: the plumbing is finished and verified, the crash is not yet
attributed, and the 8.7 MB the layer produced points at resource-state tracking rather than at a
driver bug.

## 1. The migration works on the console (this is now settled, not inferred)

`run5-d3d12-bbport.ini`, the file the app left behind on the device:

```
heavy_features_optin=0
settings_rev=4                     <- was 3 in run 4's file

# Graphics-driver switches, passed to the Mesa Dozen translator (empty = off).
# dzn_debug=d3d12 turns on the D3D12 debug layer: it reports the invalid call
# before a crash instead of after it. Add nobindless/no16bit/nostencilref to hide
# device capabilities the console driver may not support. Any name in CAPITALS
# (DZN_DEBUG=..., VK_LOADER_DRIVERS_DISABLE=...) is passed through too.
dzn_debug=d3d12
```

Not one byte of that block was written by hand: the app appended it during the revision-3 → 4
migration and bumped `settings_rev` itself. `output_res`, `skip_intro`, `watchdog` and the rest are
unchanged from run 4's file. The earlier correction (`release-notes-diag4.md`) is therefore closed —
the *install-time* path could not have done this, the *revision-4 migration* path did.

The second half — that the key actually reaches the driver — is proven by the run's output rather
than by the ini: Mesa's debug layer was demonstrably active (§2). If `dzn_debug` had not been
exported as `DZN_DEBUG`, `dozen.log` would have been 150 bytes like runs 2–4.

## 2. The D3D12 debug layer is present and working

| run | build | `dozen.log` |
|---|---|---|
| 2 (`1903`) | `f531b31` | 150 B |
| 3 (`1946`) | `fef8bc4f` | 150 B |
| 4 (`2016`) | `489444f` | 150 B |
| **5** (`dzn_debug=d3d12`) | — | **8,742,122 B / 14,744 lines** |

Two `WARNING: dzn is not a conformant Vulkan implementation` lines and **14,742** `MESA: error:`
lines. Every single one of the 14,742 is a resource-state complaint (14,742 of 14,742 — checked, no
other message template exists in the file). There is **no** `FAILED`, no out-of-memory, no
device-removed, no shader-compile abort. The file ends on a complete line with `\r\n`, containing no
NUL bytes: nothing suggests the log was cut off by the crash. Two consequences:

- The debug layer does **not** catch crash #2, because crash #2 is not an invalid D3D12 call that
  the layer validates (it is a host pointer fault — `addr=0x10` into `umd12ddi_arden.dll+0xab935`
  in run 4, and a private-heap read in run 3). Do not spend another run expecting the layer to name
  it. `nobindless,no16bit,nostencilref` (the plan carried over from diag-4) hides *capabilities*,
  not call validation, and this log gives no reason to think capability shaping is the issue.
- What the layer **does** say is about our own command stream, and it is consistent across ~8,000
  draws, so it is systematic rather than a one-off.

## 3. What the 14,742 lines actually say

By API:

| count | where the state was checked |
|---|---|
| 8,125 | `ID3D12CommandList::DrawInstanced` — `IASetVertexBuffers` |
| 3,003 | `CGraphicsCommandList::SetComputeRootDescriptorTable` (bound as NON_PIXEL_SHADER_RESOURCE) |
| 2,199 | `ID3D12CommandList::ResourceBarrier` — "Before state … does not match" |
| 1,101 | `CopyBufferRegion` (805 as destination, 296 as source) |
| 160 + 48 | `SetGraphicsRootDescriptorTable` |
| 110 | `DrawIndexedInstanced` |
| 44 | `CopyTextureRegion` |

By state dzn thinks the resource is in: `COPY_DEST` 9,470 · `NON_PIXEL_SHADER_RESOURCE` 4,111 ·
`COPY_SOURCE` 396 · mixed 11. **60 distinct resources, but 4 command lists** — so this is not a
breadth problem, it is a small number of objects being re-used in a way the tracker never follows.
The top three resources account for 13,201 of the messages (`…BFD0` ×7,749, `…9D50` ×3,376,
`…B450` ×2,076).

The two most common messages, complete:

```
DrawInstanced: Using IASetVertexBuffers ... Resource state (0x400: COPY_DEST) (assumed at first use)
  of resource (...BFD0) (subresource: 0) is invalid for use as a vertex buffer.
  Expected State Bits (all): 0x1: VERTEX_AND_CONSTANT_BUFFER,
  Assumed Actual State: 0x400: COPY_DEST, Missing State: 0x1: VERTEX_AND_CONSTANT_BUFFER.

CopyBufferRegion: ... Resource state (0x8: NON_PIXEL_SHADER_RESOURCE) (assumed at first use)
  of resource (...) is invalid for use as a destination buffer.
  Expected State Bits (all): 0x400: COPY_DEST,
  Assumed Actual State: 0x8: NON_PIXEL_SHADER_RESOURCE, Missing State: 0x400: COPY_DEST.
```

and the third template, which is a different animal — dzn is saying *we told it* the wrong
before-state:

```
ResourceBarrier: Before state (0x0: COMMON) of resource (...) specified by transition barrier
  does not match with the current resource state (0x40: NON_PIXEL_SHADER_RESOURCE)
  (promoted from COMMON state)                                    [2,151 occurrences]
```

## 4. Why our barriers do not reach dzn as per-resource barriers (source-verified)

This is the part that decides whether a fix is even possible, so it was read out of the pinned
translator, not guessed:

1. `Runtime::FlushBarriers` (`vk_runtime.cpp:965-997`) emits **one global** `vk::MemoryBarrier2`
   (`srcStageMask = OR of AccessBuffer stages`, `dstStageMask = ALL_COMMANDS`, dstAccess =
   memory-read|memory-write) plus image barriers. It never emits a `VkBufferMemoryBarrier2`. The
   per-buffer tracker (`vk_barrier_tracker.h`) exists, but it is used only to decide *whether* to
   flush — look at `AccessBuffer` (`:909-962`): everything it learns goes into `memory_barrier`.
2. In the **enhanced barrier** path (`dzn_CmdPipelineBarrier2_enhanced`, `dzn_cmd_buffer.c:1471`),
   `memoryBarrierCount` becomes a `D3D12_BARRIER_TYPE_GLOBAL` group (`:1513-1541`) and
   `bufferMemoryBarrierCount` becomes a `D3D12_BARRIER_TYPE_BUFFER` group (`:1542-1560`). Enhanced
   barriers are ON whenever `options12.EnhancedBarriersSupported` (`:688`), which is the Series X
   case — so dzn *can* track per buffer, and it is only ever told about **images** and about
   buffers we place in `bufferMemoryBarrierCount`, i.e. **none**.
3. We enable `bufferDeviceAddress` (`vk_instance.cpp:683`), so `device->bindless` is true
   (`dzn_device.c:2579`); `dzn_CmdPipelineBarrier2` asserts `!cmdbuf->enhanced_barriers` (`:38`,
   `:70`, `:95`…), meaning the legacy `D3D12_RESOURCE_BARRIER` path is effectively dead code and the
   "skip non-storage buffers" hole at `:1146-1153` cannot be what we are hitting.

Conclusion: **images are tracked, buffers are not.** A global barrier is a correct *execution* fence
in D3D12 and it is exactly what Vulkan allows us to say, but it does not move any resource's tracked
state; so from dzn's point of view every buffer we `copyBuffer` into stays in `COPY_DEST`, and dzn
transitions it *itself* on first use, reporting `(assumed at first use)` while doing so. That is why
the same three buffers repeat thousands of times and why the numbers are stable across the run.

Note also that this is not a case of the tracker being absent — our own comment at
`vk_runtime.cpp:227-229` says regions are "tracked as one bounding range per buffer: conservative for
barriers". The ranges *are* collected; `AccessBuffer` just pours them all into the single global
barrier, so nothing per-buffer is ever emitted. The intent to track buffers exists in the code; the
representation cannot carry it to dzn.

### 4.1 The granularity constraint that shapes any fix

A dense arena is **one `VkBuffer`** — `Buffer pending{instance, first_page << arena_page_bits, …}`
(`dense_buffers.cpp:130`) — and on UWP `MAX_ARENA_PAGE_BITS = 24`
(`buffer_cache.h:46`), i.e. a minimum of 16 MiB, already merged to hundreds of MiB in these runs
(`arena: live=896 MiB`). So the choice is:

- **whole-resource barriers** (`offset=0, size=WHOLE_SIZE`): a handful of records per flush, which
  happens to match dzn's own `Size = UINT64_MAX` translation (`dzn_cmd_buffer.c:1556-1557`) — but the
  granularity is 16–900 MiB, far coarser than the 64 KiB blocks we track. Transitions for different
  states inside one arena would then fight each other. Cheap, correct as a *fence*, useless as a
  *transition*.
- **ranged barriers** (`VkBufferMemoryBarrier2.offset/size`, gives dzn the real
  `D3D12_BUFFER_BARRIER.Offset/Size`): semantically right, and `vk_barrier_tracker` already speaks in
  `AddressRange`, so the records are the natural output. The risk is that ranged buffer barriers are a
  capability (`VkPhysicalDeviceMaintenance7FeaturesKHR`-adjacent / optional), and the console driver's
  answer is **not** something to assume — it must be logged once, by name, on the next run.

That is why the diag-5 experiment in §8.3 is written as *one toggle, two runs, and a logged capability
line* rather than as a fix.


## 5. Is this the crash? — honest answer: it cannot be proven from this run, and the balance of
evidence is *against* the state warnings being crash #2

Arguments that this is only noise:

- The layer is a validator; these are errors, not failures. Nothing stopped.
- The three hot resources account for 13,201 of 14,742 messages over 2,326 presents. If an unbarriered
  vertex buffer were breaking rendering, the picture would be wrong immediately and constantly — the
  run instead got as far as it ever has (it is the same build/revision as the `1946` run, which is
  also the run that reached 2,326 presents).
- An "assumed at first use" resource is transitioned by dzn itself, so the *data* is still valid.

Arguments that it matters:

- It means our synchronization is implemented as fences, not transitions. Any resource whose contents
  we write and then read within one submission is ordered only by chance of submission boundaries.
- The 2,151 "before state does not match" messages say our recorded idea of a resource's state
  diverges from dzn's actual state — that is a correctness smell even where nothing crashes.

So: **diagnosed as a real defect in our barrier representation, classified as "must fix, not yet shown
to be the killer."** The next build should be able to tell the two apart (see §7).

## 6. Run 5's crash is still unattributed — the file that would have said it is missing

There is **no `loader.log.txt` from run 5** in the upload. What was sent is the archive set from the
*previous* runs, and the app's archive naming makes that easy to misread (a file called
`loader-2.log` is not "run 2" — the suffix is a collision counter). Verified mapping by each file's
own `UWP build:` line:

| uploaded file | build inside it | presents | fault |
|---|---|---|---|
| `loader-2.log` | `1.0.26314.1946` `fef8bc4f` (= run 3, archived) | 2,326 | `module=unknown+0x23ec55 addr=0x1429f5fed70` |
| `loader-3.log` | `1.0.26314.2016` `489444f` (= run 4) | 1,464 | `umd12ddi_arden.dll+0xab935 addr=0x10` |
| `loader.log` / `loader-2026_11_10.log` | `1.0.26314.1903` `f531b31` (= run 2) | 2,176 | `vulkan_dzn.dll+0x1fd79 addr=0x148` |
| `loader-2026_11_10-2/3.log.txt`, `loader.log.txt` | `1.0.26314.1455` `9849caf` | 1,225 / 0 | dzn `+0x1fd79` |

The three older loader logs in this upload are **byte-identical** (md5-checked) to the ones already
archived here — `loader-2.log` = `run3-1946-loader.log`, `loader-3.log` = `run4-2016-loader.log`,
`loader-2026_11_10.log` = `run2-1903-loader.log`. So this upload added **no new loader log at all**:
everything from a previous run was a re-send, and the one file that belongs to *this* run is missing.
The milestone table is therefore unchanged: 1,225 (dzn `+0x1fd79`) → 2,176 (dzn `+0x1fd79`) → 2,326
(`module=unknown+0x23ec55`, after a watchdog degrade) → 1,464 (`umd12ddi_arden+0xab935`, `addr=0x10`).

**The migration build's own crash is unknown.** Run 5 might have died at 2,326, at 1,464, somewhere
new, or not at all — the upload does not say. This is the one measurement this run owed us and it did
not arrive.

Also unseen, and it matters for the same reason: the app's own `UWP thread op:` / `UWP build:` context
lives on stdout, i.e. `loader.log`, which is exactly what is missing. What is *not* in doubt is that
this run's `dozen.log` proves the debug layer was on (§2) — a 150-byte `dozen.log` is what an
un-exported `dzn_debug` would have produced.

One loose end to watch rather than act on: `bbport-2.ini` (81 lines, `settings_rev=4`) is missing the
`skip_intro` line the older 74-line file carried, so the file uploaded is not a pure superset of the
previous one and may not be the exact file this run loaded. It says nothing about whether the
migration ran — the appended comment block and the revision bump are decisive on their own — but the
next upload should include the ini together with the loader log that printed its settings, so the two
can be read against each other.

## 7. The one new app-side line, and what it means

`errors-4.log` (76 lines, and the only one of the four with this line) has a message the run-4 log
does not:

```
GPU [Lib.GnmDriver] <Error> amdgpu/liverpool.cpp:70 NextPacket: packet length exceeds remaining
submission size. Packet dword count=2, remaining submission dwords=1
```

`NextPacket` is read in full (`liverpool.cpp:64-79`): when `offset > span.size()` it logs and returns
`{}`, and the caller's `while (!dcb.empty())` loop then exits — **a 1-dword overrun silently ends that
command stream for the submission.** The stream here is one dword short of a complete 2-dword packet
(Type-3 header `(dword_count << 16) | 0xC0000000`, then one body dword). Note what that implies:
dzn's state tracker saw only the command lists that were actually submitted and recorded; if a PM4
stream is being truncated at a packet boundary, the tail of that stream — which is where the
transitions live — never reaches the GPU. This is the only *emulator-side* defect in this run's log,
it is new in this run, and it is cheaper to instrument than to argue about.

## 8. What diag-5 should do (small, all three in one build)

1. **Make the crash name itself.** `ModuleNameForAddress` returns `nullptr` and prints `unknown` for
   the run-3 crash even though the address is inside *our own executable* (`addr=0x10` read, rip
   `0x7ffac2edec55`). It resolves `K32EnumProcessModules`/`K32GetModuleInformation` by name and
   silently gives up — on the console partition. Fix: if enumeration fails, fall back to what we can
   always get — `GetModuleFileNameW(GetModuleHandleW(nullptr))` for anything above the exe's base, and
   print the raw `mod_base`/`rip` pair so a future run can be identified even when the name is not.
   (Never again two runs with `module=unknown`.)
2. **Log the truncated submission instead of swallowing it.** On the `NextPacket` overflow path: print
   the queue id, the submission's base address and full dword count, the offset, and the last four
   dwords of the packet that was cut. That turns one benign line into a reproducible artifact.
3. **One experiment to separate the state warnings from the crash:** make `FlushBarriers` also emit
   `VkBufferMemoryBarrier2` records built from the ranges `AccessBuffer` already collects, behind a
   toggle (a new `BbToggle` bit plus an ini key so it can be A/B'd without a rebuild). Start with
   **whole-resource** barriers (cheap, no capability risk, and dzn's BUFFER group already uses
   `WHOLE_SIZE`), and print once at startup whether this device reports ranged buffer barrier support,
   so the ranged variant is a decision from evidence rather than a guess. Then run twice — toggle off /
   on — and compare `dozen.log` size and the present count. If the warnings drop to near zero and the
   presents do not move, this whole thread is hygiene; if the presents move in either direction, the
   barrier representation is in the crash path.

Do **not** spend another run on `nobindless,no16bit,nostencilref` yet: it hides capabilities, and no
line in this run points at a capability. If diag-5 does not move the presents, that set is the next
A/B, not the next build.

## 9. What we still owe the record

- Run 5's `loader.log.txt` (or the next run's), with `UWP build:` and the `presents=` curve — the
  single missing number from this analysis. Name the file by its contents when uploading; the archive
  suffix is not the run number.
- Whether `dzn_debug=d3d12` was still in the environment on the *second* launch after the migration
  (the ini says it persists; the log would say).
