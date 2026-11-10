# Run 6 — no crash, a stall, and 6 fps: the first run that got past the fault

Evidence: `dozen-3.log` (14,536,906 bytes, 24,411 lines) and `errors-5.log` (19,281 bytes, 75 lines),
uploaded with the user's words: *"game didnt crash just stuck and its only 6fps"*. No `loader.log` this
time either, so there is **no present count, no build string and no stall report** — everything below
comes from the two files that were sent, and each claim says how much it depends on that gap.

## 1. The fault did not happen

`errors-5.log` contains **zero** `UNHANDLED` lines. The only difference from the previous run's
`errors.log` is one line that is now *absent*:

```
- GPU [Lib.GnmDriver] <Error> liverpool.cpp:70 NextPacket: packet length exceeds remaining
-   submission size. Packet dword count=2, remaining submission dwords=1
```

That is a real signal, not an artifact: the truncated submission of the previous run is gone, and
nothing replaced it. So the D3D12Core fault (`+0x240d96`, `addr=0xFFFFFFFF000001B8`, the
`slot == -1` device address) **did not occur in this run**. Whether that is because the run never
reached the phase that takes that address, or because something changed, cannot be settled without
the loader log's present count — the two runs' `dozen.log` sizes (8.7 MB vs 14.5 MB) say this one drew
*more*, not less, so "it got further" is the likelier reading.

## 2. The 6 fps is very likely the debug layer we deliberately left on

The `dzn_debug=d3d12` path was **still active in this run**: `dozen.log` is 14.5 MB, i.e. the layer
is emitting again. And the rate is identical per draw to the previous run:

| run | debug-layer messages | `DrawInstanced` calls | messages per draw |
|---|---|---|---|
| 5 (`d3d12`) | 14,742 | 8,125 | **1.81** |
| 6 (this) | 24,409 | 13,642 | **1.79** |

Every message is a `fprintf` to a redirected handle, flushed, on the *recording thread* — 24,409 of
them for 13,642 draws. That is a plausible direct cause of a 6 fps ceiling on its own, and it is the
one cause we control perfectly: **turn the layer off and measure again.** Until that is done, 6 fps
should not be attributed to anything else.

Two caveats, stated rather than hidden: we do not have a present count for this run, so "6 fps" is the
user's observation, not a logged number; and if the game is also *stuck* (presents stopped), then fps
and stall are two different problems and the layer only explains the first.

## 3. What the layer still reports is unchanged, and now much bigger

24,409 resource-state messages over **4 command lists and 60 resources**. The mix is the same three
shapes as before — 13,642 "invalid for use as a vertex buffer", 5,068 "invalid … as
NON_PIXEL_SHADER_RESOURCE", 3,366 "Before state … does not match" — and the top three resources carry
23,946 of them (`…BB50` 13,079, `…AA10` 5,606, `…98D0` 3,261).

The important number: `DrawInstanced` messages reference **2 distinct resources**. So the entire
per-frame vertex cost of this scene goes through two buffers that dzn must transition itself, on
first use, every time, because we never tell it their state. That is the barrier defect already
written up in `hardware-run-2026-11-10-run5-d3d12-layer.md` §4 — and in this run it is not a
curiosity, it is on the hot path of every draw.

## 4. What to do next, in strict order

1. **Turn the debug layer off** (`dzn_debug=` empty in `bbport.ini`) and run once more. This is not a
   new build; it is a settings edit. It answers: *is 6 fps the layer, or the game?* If fps jumps and
   the stall remains, the stall is the real target and the layer was the entire fps story.
2. **Send `loader.log.txt` with that run.** It is the second run in a row without it, and it is the
   only file that carries `presents=`, `UWP build: version=`, the STALL DETECTED block and the thread
   report. Every question left open above is answered by it.
3. Only then decide between the two real defects:
   - the **buffer state tracking** (two hot vertex buffers, per-draw transitions) — this is now
     justified by measurement, not by theory, and its design is already in §4.1 of the run-5 doc;
   - the **device address from `slot == -1`** (`dzn-buffer-address-slot-minus-one.md`), which did not
     fire this run but is unfixed and will fire again the moment the game reaches that phase.

Do not change two things at once: the layer-off run is worth nothing if a new build goes in with it.
