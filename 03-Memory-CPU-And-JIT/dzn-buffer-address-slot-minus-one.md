# The run-5 crash is arithmetically identified: a bindless buffer address built from slot `-1`

Evidence: `hardware-run-2026-11-10-26314-logs/run5-2112-loader.log` line 3006, plus the pinned dzn
sources (`Cosmo/mesa_ai_slop_version` @ `a76cd3caa23f`):

- `src/microsoft/vulkan/dzn_private.h:1291` — `int uav_bindless_slot;`
- `src/microsoft/vulkan/dzn_device.c:3288` — `buf->cbv_bindless_slot = buf->uav_bindless_slot = -1;`
  (the "no slot" state, set before allocation)
- `src/microsoft/vulkan/dzn_device.c:3289` — allocation happens **only** `if (device->bindless)`
- `src/microsoft/vulkan/dzn_device.c:3948-3955`:
  ```c
  dzn_GetBufferDeviceAddress(VkDevice device, const VkBufferDeviceAddressInfo* pInfo)
  {
     struct dzn_buffer *buffer = dzn_buffer_from_handle(pInfo->buffer);
     /* Insert a pointer tag so we never return null */
     return ((uint64_t)buffer->uav_bindless_slot << 32ull) | (0xD3ull << 56);
  }
  ```

## The arithmetic

The fault line is:

```
UNHANDLED NATIVE FAULT: code=0xc0000005 module=D3D12Core.dll+0x240d96
                       rip=0x7ffac2ee0d96 rsp=0x1908fff300 addr=0xffffffff000001b8
UNHANDLED FAULT CONTEXT: addr is not mapped
```

With `uav_bindless_slot == -1`:

```
((uint64_t)(-1) << 32) & 0xFFFFFFFFFFFFFFFF   = 0xFFFFFFFF00000000
| (0xD3ULL << 56)                             = 0xFFFFFFFF00000000   (tag already inside)
+ 0x1b8  (field offset inside the structure)   = 0xFFFFFFFF000001B8
run 5 `addr=`                                  = 0xFFFFFFFF000001B8   <-- exact, all 16 digits
```

The `0xD3` tag in the driver's own code is the clincher: this address is not a pointer that went bad,
it is **dzn's fabricated buffer address format**, computed from a slot that was never allocated. A
64-bit value whose top half is `0xFFFFFFFF` and whose bottom half is a small offset is `(int)-1` shifted
into the high 32 bits — i.e. `slot = -1` — plus `0x1b8`.

## Why this happens, and what it means

`dzn_GetBufferDeviceAddress` returns a *fake* address that is really "which descriptor slot is this
buffer" in the top 32 bits. Shaders that use a raw buffer address (Vulkan `bufferDeviceAddress`,
GLSL `buffer_reference`) get that value, and dzn's generated code later indexes a structure from it.
When the slot is `-1`, the base is `0xFFFFFFFF00000000` and every access lands at `-1<<32 + field` —
exactly the fault address. The field is at `+0x1b8`.

So: **a buffer was created without a bindless slot (so `uav_bindless_slot` stayed `-1`) and the game
took its device address anyway.** Two ways that happens:

1. **Bindless active** (`device->bindless` true on the console, because we enable
   `bufferDeviceAddress` + `descriptorIndexing`, `vk_instance.cpp:683`): the slot *should* have been
   allocated for any buffer with `SHADER_DEVICE_ADDRESS_BIT` (line 3297-3298), so a `-1` here means a
   buffer was handed out whose usage bits did not include the storage/device-address bits at creation —
   i.e. **our** usage flags are wrong for a buffer we then address.
2. **Bindless inactive** (`dzn_debug=nobindless`): `device->bindless` is false, no slot is ever
   allocated, every `uav_bindless_slot` stays `-1`, and every device address is
   `0xFFFFFFFF00000000 | tag`. The fault then becomes *the expected result of the switch*, not a fix.
   `dzn_device.c:715` only disables the *feature advertisement* (`descriptorIndexing`), which should
   stop a conformant client from asking — but this driver still returns a fabricated address.

**Consequence for the experiment I was about to recommend:** `dzn_debug=nobindless` is *not* a clean
A/B. It may make the crash disappear by making device addresses invalid everywhere, which would look
like a success and teach nothing. Keep it as a second-tier probe only, and read the result as "does
the app still take device addresses at all", not as "bindless was the bug".

## The next build's target, precisely

The actionable defect is on **our** side of the boundary: a buffer we bind and take the device address
of is created without `VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT` (and/or without
`VK_BUFFER_USAGE_STORAGE_BUFFER_BIT`), so dzn never allocates its slot, and
`dzn_GetBufferDeviceAddress` fabricates an address from `-1`. That is checkable in one build with no
guesswork:

- At buffer creation, assert/log when `usage` lacks `SHADER_DEVICE_ADDRESS_BIT` but the buffer's
  address is later requested (`GetBufferDeviceAddress`), naming the buffer, its size, its source
  (arena / staging / dedicated) and the guest range it backs.
- The same for the reverse: a buffer whose `VK_BUFFER_USAGE_*` set cannot be upgraded after creation,
  which is where the "our usage flags are wrong" case would come from.

If the log then points at the arena/staging path (`dense_buffers.cpp`, `vk_staging_buffer_pool.cpp`),
the fix is to create those buffers with the device-address + storage bits. If it points at a
texture's buffer or a ring block, the fix is local to that allocation. Either way it is a one-line
usage-flag change plus the assertion that found it.

## Status of the other candidate threads

- **Buffer-state (barrier) warnings from the debug layer:** not involved. 14,742 warnings, no
  relation to a device address. Stays a hygiene item; do not spend the next build on it.
- **The asset-load stall** (presents frozen at 1,764 while seven arenas and seven resolution proxies
  were allocated in one second): the stall is real and happens *before* the fault, but the fault now
  explains itself completely and does not need the stall. Treat the stall as the next-next target, and
  note the watchdog failed to take its own 10 s exit during it (a separate two-line bug).
