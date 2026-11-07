# Xbox UWP Dev Mode — Memory & System Caps (Xbox One vs Series X|S)

Status: STUDY COMPLETE (2026-11-07). Confidence labels: **PRIMARY** = Microsoft-owned page,
**CORROBORATED** = 2+ independent sources, **SINGLE-SOURCE** = one source, treat as claim.

## 1. The numbers

| Resource | UWP "App" class | UWP "Game" class | Confidence |
|---|---|---|---|
| Memory (foreground) | **1,024 MiB** (tools may show ~1.3 GB virtual) | **5,120 MiB (5 GB)** | PRIMARY [S1][S2], CORROBORATED [S3][S4][S5][S6] |
| Memory (background) | 128 MiB | (suspended; over-budget ⇒ terminate) | CORROBORATED [S4] |
| CPU | shared slice of 2–4 cores | **4 exclusive + 2 shared cores** | CORROBORATED [S4][S5] |
| GPU | up to ~45 % | full GPU | CORROBORATED [S4][S5] |
| Single file size (Dev Mode) | **2 GB max per file** | same | CORROBORATED [S4][S5] |
| Dev storage (sideload quota) | 5 GB default ("Manage Dev Storage" to raise) | same | SINGLE-SOURCE [S7] |
| JIT code cache | 128 MiB per core | same | SINGLE-SOURCE [S6] |

**Xbox One vs Series X|S: the UWP sandbox cap is the same 5 GB on both.** The 5 GB exists to
hold across the Xbox One generation; Series X|S UWP titles do **not** get the console's full
16 GB ("What does Series X use the other 11 GBs for?" — nothing you can have) [S1][S3].
Series hardware still helps: faster CPU/GPU/SSD within the same sandbox.

## 2. The classification switch (Xbox-specific, the #1 gotcha)

A package is *not* a game because it is a game — it must be **classified as "Game"**:

- Dev Mode → Settings → Preferences → **"Treat UWP apps as games by default"** [S5], or
- per-title in **Xbox Device Portal / Dev Home: App → Game** [S6][S3].

Miss this and the app runs in the 1 GB budget and dies at startup with **`0x8007000E`
(`ERROR_OUT_OF_MEMORY`) — "quits nearly instantly on Xbox"** [S3]. This is the single most
common Dev Mode failure and it is a *classification* problem, not a leak.

## 3. APIs for staying inside the budget

- `Windows.System.MemoryManager`: `AppMemoryUsage`, `AppMemoryUsageLimit`,
  `AppMemoryUsageLevel`, `TrySetAppMemoryUsageLimit` — process memory budget telemetry.
- GPU: `IDXGIAdapter3::QueryVideoMemoryInfo` (per-segment budget) — this is what Dawn's
  D3D12 `ResidencyManager` reads before evicting LRU pageables (`ResidencyManagerD3D12.cpp`,
  budget = 95 % of the OS budget minus external reservation).
- JIT W^X: `codeGeneration` capability + `VirtualProtectFromApp` for RX↔RW transitions.
  The 128 MiB/core JIT cache claim [S6] is single-source — measure before relying on it.

### Drop-in budget telemetry (C++/WinRT)

```cpp
#include <winrt/Windows.System.h>

void log_memory_budget(const char* tag) {
    auto mm = winrt::Windows::System::MemoryManager();
    printf("[%s] usage=%llu MiB  limit=%llu MiB  level=%d\n", tag,
           (unsigned long long)(mm.AppMemoryUsage() >> 20),
           (unsigned long long)(mm.AppMemoryUsageLimit() >> 20),
           (int)mm.AppMemoryUsageLevel());
}

// Startup guard: classify OOM-at-launch distinctly (the App/Game gotcha).
void* guarded_alloc(size_t n) {
    try { return malloc(n); /* or any WinRT allocation */ }
    catch (const winrt::hresult_error& e) {
        if ((uint32_t)e.code() == 0x8007000E) // ERROR_OUT_OF_MEMORY
            fatal("Out of budget at startup — is the package classified as 'Game' in Device Portal?");
        throw;
    }
}
```

## 4. Documented failure modes

1. **`0x8007000E` at launch** — package classified as App (1 GB) but sized for Game (5 GB) [S3].
2. **Suspend-and-terminate** — games exceeding the budget are suspended and killed [S4];
   backgrounded apps get 128 MiB [S4].
3. **2 GB per-file ceiling (Dev Mode)** — a Wii ISO/RVZ > 2 GB cannot be opened at all [S4][S5].
   GameCube images (≤ ~1.35 GB) fit; dual-layer Wii content does not. Plan content pipelines
   around chunked/compressed containers or USB + streaming.
4. **Sideload failure with a misleading error** — dev storage default 5 GB; a > 5 GB package
   fails with an unrelated error until "Manage Dev Storage" raises the quota [S7].
5. **JIT thrash** — if the 128 MiB/core JIT cache figure [S6] holds, code caches must be
   generation-managed; unbounded JIT growth hits either the code cache or the 5 GB wall.

## 5. Port implications (this project)

- The Melee-class target (GC-era) fits 5 GB with margin **as a Game**; the classification
  toggle is part of every install checklist (it lives in Device Portal, not the manifest —
  `Package.appxmanifest` for this project contains no `expandedResources`; see
  `../01-Core-Architecture/packaging-and-deployment.md`).
- Caches on internal `D:\developmentfiles\<App>` only; USB for content (project convention,
  see packaging study). Respect the 2 GB file cap when designing disc-image handling.

## Sources

- [S1] Microsoft Q&A, "Why i only have 1.3gb to use in Xbox Dev Mode" — learn.microsoft.com/answers/questions/5878918 (PRIMARY, Microsoft-hosted)
- [S2] Microsoft Learn, "System resource allocation" (UWP on Xbox) — learn.microsoft.com/previous-versions/windows/uwp/xbox-apps/system-resource-allocation (PRIMARY, referenced by S1/S3)
- [S3] Unity Discussions, "UWP Quits Nearly Instantly on XBOX" (0x8007000E diagnosis, App→Game toggle) — discussions.unity.com/t/uwp-quits-nearly-instantly-on-xbox/949731
- [S4] TechRepublic, "Xbox Series S and X Developer Mode" (2 GB file cap, 128 MB background, CPU/GPU split) — techrepublic.com/article/xbox-series-s-and-x-developer-mode-3-things-you-can-do-with-it-and-3-you-cant/
- [S5] blog.vinfall, "Xbox Dev Mode" (Dev Mode quirks, "Treat UWP apps as games by default") — blog.vinfall.com/posts/2023/06/xbox-dev-mode/
- [S6] WindowsForum, "Eden-Xbox … D3D12 Limits" (5,120 MiB ceiling, Device Portal App→Game, JIT 128 MiB/core) — windowsforum.com/news/eden-xbox-brings-switch-emulation-to-xbox-series-x-developer-mode-with-d3d12-limits.448640/ (SINGLE-SOURCE for JIT cache figure)
- [S7] Stack Overflow 65325070 (dev storage 5 GB default, misleading sideload error)
