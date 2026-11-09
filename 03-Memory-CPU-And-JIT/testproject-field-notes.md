# Field Data — `youdedend/Test-project` on real Xbox Series S (Tests #11–#29)

Status: FIELD EVIDENCE (2026-11-07 snapshot of `arena/8ac58bdb-test-project` /
`PROJECT_COMPLETE_HISTORY.md`). This file is the measured counterweight to
`dev-mode-memory-and-system-caps.md`'s secondary-sourced numbers — console telemetry beats
forum posts per our evidence rules.

## 1. What the project is (context)

UWP port of `Supermedo/bloodborne_pc` (bbport: native x86-64 guest + HLE Orbis shims + shadPS4
Liverpool GPU code). **Not full emulation** — no guest recompiler, no 8 GB guest RAM model.
Vulkan runs on Xbox via packaged **Mesa Dozen** (`vulkan_dzn.dll`, `Cosmo/mesa_ai_slop_version`
@a76cd3ca, MSVC 14.44) under a D3D12 `CoreWindow` bridge. Signed `.appx` built in GitHub
Actions (clang-cl + `check-imports.ps1` against `WindowsApp.lib`).

## 2. Measured values (Series S, Game Mode, 5,120 MiB)

| Measurement | Value | Source |
|---|---|---|
| Title/menus | 29.4–29.5 FPS, 0.85 ms present | handoff.md §2 (Tests 1–10) |
| Central Yharnam live 3D | **25.8 FPS**, `presents=1885`, swap out=808/in=250/disk=572 MiB, `corrupt=0` | handoff.md §2 |
| Startup footprint (`presents=0`) | 1,001–1,003 MiB | handoff.md Test #12 acceptance |
| Yharnam telemetry class | 4,135 MiB @ presents=1376 (Test 11 crash run) | docs/hardware-test-11 |
| Crash/stall wall (extended play) | **5,055–5,116/5,120 MiB** after 800–1,300 presents | Tests 15–29 timeline |
| Guest-page swap compression | 1,439 MiB pages in 713 MiB file (Test 27); 1,149→483 MiB (Test 28/29) | hardware-test-27/29 |
| Shader cache | `driver.vkcache` 173,715 KiB; WarmUp 121/121 pipelines | handoff.md §2 |
| DeviceLocal alloc failure | 16 MiB refused at 5,116/5,120 MiB (Test 15) | history timeline |
| End-of-run failure classes | `vmaCreateBuffer → -2` (Tests 20–21), swap-disk ceiling stall (22–23), volume write refusal ~1,171 MiB (24), storage exhaustion (25), `VK_ERROR_DEVICE_LOST` ~4,989 MiB (28/29) | hardware-test-\*/README.md |

## 3. Pager/swap design facts (generalizable)

- Guest pages paged to sparse `LocalState` file (`garlic_swap.bin`), **WC_GARLIC only**, never
  ONION/guest_code; fault-time pinning of CPU-touched pages.
- Self-imposed disk budget bites first: 768 MiB (`.736`) → grow-on-demand 256 MiB steps to a
  1 GiB ceiling (`BB_UWP_SWAP_DISK_MB` hard cap, default 2,048 in `.935`) — the console device
  never refused a write before the budget did (`full=0` with 1,209 MiB unwriteable pages).
- Compression: 16 KiB record collision bug (raw-page marker vs exact-16-KiB compressed record)
  — fixed; blank pages (20,604 of 125,940) stored for nothing — zero-page elision candidate.
- 768 MiB live arena cap + 250 MiB admission reserve are **observation-only, not enforced**;
  enforcing needs a fail-soft caller contract (draw/dispatch/readback/DMA demand contiguous
  `Buffer*`) — the single most important open problem in the project.
- `ERROR_DISK_FULL` / volume-refusal at ~1.1 GiB on the chosen volume → swap volume selection
  (`swap_auto`, never USB, D:-preferred) is unverified inside AppContainer (bus queries may
  be denied → silent fallback to Q:).

## 4. Corrections this data forces on our research claims

1. **"Native ports ≥6 GB free > 5,120 MiB ⇒ hard NO" is falsified** — the PC figure includes
   pagefile; with guest-page paging the engine fits and plays. Verdict revised in
   `../01-Core-Architecture/bloodborne-xbox-uwp-feasibility.md`.
2. **"No Vulkan on UWP ⇒ full renderer rewrite" overstated** — packaging Mesa Dozen (Vulkan
   over D3D12) preserved the Vulkan renderer. Cost moved to Dozen conformance quirks
   (`nir_to_dxil` `OpUnreachable` handling, `dzn_pipeline.c` binding asserts — see
   `Test-project` `handoff.md` §5 dead-ends 8–10).
3. The **2 GB per-file Dev Mode claim remains untested here** — but `.935`'s default swap
   budget is exactly 2,048 MiB, which will falsify or confirm it when the swap file grows
   past 2 GiB. Watch `write failures` in the pager line on the next console run.

## 5. Cross-map: our findings → their open items

| Their open item | Our finding that applies |
|---|---|
| #3 watchdog + 5 s save-flush deadline | Suspension contract D-S1–D-S7 (BLIND SPOT #3.5/3.6): WILL/DID channels, quiesce on DID, flush ≪ 5 s |
| #2 allocation admission / arena cap | B1.1 admission control (BLIND SPOT #3): reserve first, retire at frame boundaries only |
| #1 swap volume selection | Packaging study: caches on `D:\developmentfiles\<App>`, USB content-only convention; per-file caps |
| Gamepad/deadzone item | WGI study: empty-list 1–2 s quirk, hot-swap erase, mutex; B/Back-suspends |
| Provisioning/Device Portal item | package.ps1 case study + CSRF/`X-Auth` token flow for Device Portal API |
