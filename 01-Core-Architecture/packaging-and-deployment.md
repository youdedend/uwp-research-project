# Xbox UWP — Packaging & Deployment (.appx, signing, Device Portal) — with the Melee package as case study

Status: STUDY COMPLETE (2026-11-07) — primary-source driven from
`YTReviveMe/melee-UWP.` @ `UWP-Port`: `platforms/xbox/package.ps1`, `Package.appxmanifest`,
`platforms/xbox/README.md`.

## 1. The pipeline (what `package.ps1` actually does)

1. **Version gate**: package version must be `X.Y.Z.N` matching `VERSION` `vX.Y.Z` — mismatch
   throws before anything is staged.
2. **Payload staging**: `melee.exe`, `SDL3.dll`, `nod.dll`, `libpng16.dll`, `zlib1.dll`,
   `resources/`, `licenses/`. Dependency package
   `Microsoft.VCLibs.x64.14.00.appx` (from the Windows Kits ExtensionSDK) is required and
   shipped alongside.
3. **Policy guard**: staging is scanned for disc images (`.iso .gcm .ciso .rvz .gcz .wia`) —
   any hit aborts the build. The package **must not contain game content** (see
   `licenses/LICENSE.md` note in the README). This is both legal hygiene and a Store/WACK
   review risk reducer.
4. **Assets**: `StoreLogo.png` 50×50, `Square44x44Logo.png`, `Square150x150Logo.png`,
   `SplashScreen.png` 620×300 — generated from `Assets/Icon.png` via System.Drawing. These
   sizes are hard manifest requirements (missing/mis-sized logos fail packaging/first-run).
5. **Pack**: `makeappx.exe pack /d <stage> /p <name>_<version>-x64.appx /o` (Windows Kits
   10.0.26100.0). Plain `.appx`, x64, not `.msix`.
6. **Sign** (`-Sign`): reuse a `CN=<Publisher>` CodeSigning cert if valid > 30 days, else
   `New-SelfSignedCertificate -Type CodeSigningCert` (SHA256, non-exportable, 2 years);
   `signtool sign /fd SHA256 /sha1 <thumb> /s My`; `signtool verify /pa`; export
   `MeleeUWP.cer`.
7. **Deploy**: install `appx` + `.cer` + VCLibs through **Xbox Device Portal** (Dev Mode).
   Dev storage quota default is 5 GB — oversized packages fail with a misleading error until
   "Manage Dev Storage" is raised [S1].

## 2. Manifest anatomy (the real one, abridged)

```xml
<Identity Name="MeleeUWP" Publisher="CN=MeleePC.XboxDev" Version="0.4.2.1"
          ProcessorArchitecture="x64" />
<TargetDeviceFamily Name="Windows.Universal" MinVersion="10.0.19041.0"
                    MaxVersionTested="10.0.26100.0" />
<PackageDependency Name="Microsoft.VCLibs.140.00" MinVersion="14.0.0.0" />
<Application Id="App" Executable="melee.exe" EntryPoint="MeleePC.App">
  <Extensions>
    <uap:Extension Category="windows.fileTypeAssociation"> … .iso .gcm .rvz .gci .dds …
  </Extensions>
</Application>
<Capabilities>
  <uap:Capability Name="removableStorage" />   <!-- USB content -->
  <Capability Name="internetClient" />
</Capabilities>
```

Xbox-relevant facts:
- **No `expandedResources` / no Game flag in the manifest.** App-vs-Game classification
  (1 GB vs 5 GB memory) is a **Device Portal / Dev Home toggle** on console, not manifest
  metadata — see `../03-Memory-CPU-And-JIT/dev-mode-memory-and-system-caps.md` §2.
- `removableStorage` + the file-type association are what make the USB disc browser and the
  `D:\developmentfiles\<App>` layout legal. Dev Mode additionally caps **individual files at
  2 GB** (memory study §1).
- Storage layout convention (primary README): app creates
  `D:\developmentfiles\Melee\{cache,textures,music,saves,settings}`; USB drives get the same
  folders **except `cache`** — "Graphics and network caches always use D:". Deliberate: keeps
  caches off removable media (USB yank/latency; cf. the cache-on-removable-storage hazard).
- Toolchain note: game code built with **MinGW GCC to preserve big-endian disc structures**;
  UWP platform code with clang-cl; disc reader (`nod`) is Rust targeting
  `x86_64-uwp-windows-msvc` with `-Z build-std=std,panic_abort` (pinned `encounter/nod@ebd80ca`).

## 3. Failure modes (documented)

1. **Misleading sideload error at the 5 GB dev-storage default** [S1] — raise "Manage Dev
   Storage" before deploying big packages.
2. **Cert expiry**: the sign step requires an existing cert with > 30 days validity; as the
   self-signed cert nears its 2-year expiry, installs on other devices fail (`.cer` must be
   re-exported and re-trusted on the console).
3. **Version mismatch throw** (package.ps1) — CI-friendly hard failure; keep `VERSION` and
   manifest `Version` in lockstep (4th digit auto-build number).
4. **Disc image in package** — aborts build by design; shipping one is a license/Store
   rejection risk regardless.
5. **`0x8007000E` at first launch** — not a packaging failure but the App/Game
   misclassification; happens *after* a successful install (memory study §4).

## 4. WACK / Store status (partial)

- WACK = Windows App Certification Kit, run against the package before Store submission;
  its "Supported API" test is what would flag desktop-partition APIs (e.g. user32 `IsWindow`,
  which Dawn's HWND surface validation references — see the BLIND SPOT #4 note). Dev Mode
  sideloading skips WACK entirely; **Store/retail submission is a separate, unstudied gauntlet**
  (Creators Program for games, see [S2] in the memory study).
- `package.ps1` produces Dev Mode artifacts only (`.appx` + `.cer` + VCLibs); no Store
  bundle/`.msixupload` path exists yet.

## Sources

- Primary: `YTReviveMe/melee-UWP.` @ `UWP-Port` — `platforms/xbox/package.ps1`,
  `platforms/xbox/Package.appxmanifest`, `platforms/xbox/README.md`, `VERSION`,
  `licenses/LICENSE.md` (referenced).
- [S1] Stack Overflow 65325070 (dev storage 5 GB default, misleading error).
- [S2] Microsoft Q&A 5878918 (Creators Program game classification) — learn.microsoft.com/answers/questions/5878918.
