# Package staging (templates — nothing here is installable yet)

Phase 4 turns this folder plus build outputs into a signed `.msix`. Until then, everything here is a reviewed template.

## Files

| File | Role |
|---|---|
| `Package.appxmanifest` | UWP manifest template. `CHANGE-ME` identity fields, x64, VCLibs dependency declared, v1-minimal capabilities. Read its header comment before touching capabilities |
| `Config.toml` | Runtime config for `LocalState\NSMBW\Config.toml`; pins the `../GameAssets/DATA` game-data contract and conservative Series S video defaults |
| `Assets/` (you create it) | Your own placeholder tiles — **no game artwork**. Required PNGs (32-bit, with alpha), same set the recipe documents: `StoreLogo.png` 50×50, `Square150x150Logo.png` 150×150, `Square44x44Logo.png` 44×44, `SplashScreen.png` 620×300, plus `Wide310x150Logo.png` 310×150 named by our manifest |

Generate flat placeholder tiles with ImageMagick if you have it (from the recipe’s asset guide):

```powershell
$tiles = @{ 'StoreLogo.png' = '50x50'; 'Square150x150Logo.png' = '150x150'
            'Square44x44Logo.png' = '44x44'; 'SplashScreen.png' = '620x300'
            'Wide310x150Logo.png' = '310x150' }
foreach ($t in $tiles.GetEnumerator()) {
  magick -size $t.Value xc:"#1b1b1f" (Join-Path 'ports\nsmbw-xbox\package\Assets' $t.Key)
}
```

## What the Phase 4 staging step assembles

```text
<staging>\
  NSMBW.exe                 linked AppContainer binary (renamed from the WiiCompiled target)
  SDL3.dll                  TRUE UWP build (from the separate verified bundle - never a desktop SDL)
  webgpu_dawn.dll nod.dll* dxcompiler.dll dxil.dll libpng16.dll z.dll libuwp.dll
  dsp_coef.bin              upstream runtime asset (from the PC build output)
  initial_pipeline_cache.db upstream runtime asset (keep the kill-switch test in Phase 5 in mind)
  wii_bootstrap\            upstream runtime asset tree
  AppxManifest.xml          this folder's manifest, identity filled in, version bumped
  Assets\*.png              your placeholder tiles
```
`*` only if the Phase 2/3 link actually pulls that library — the staging script must derive the DLL list from the linked binary’s imports, not from this table.

**Never staged:** game data (`GameAssets\DATA` goes to `LocalState` via Device Portal), generated game code as loose files, saves, certificates/keys, PC `UserData` folders, or the whole `work/` tree.

## Identity checklist (before `makeappx`)

- [ ] `Identity/@Publisher` is byte-identical to your signing certificate subject (`Get-ChildItem Cert:\CurrentUser\My | Format-List Subject, Thumbprint`).
- [ ] `PhoneProductId` is your own GUID, not the template’s.
- [ ] `Identity/@Version` is higher than every previously installed build.
- [ ] `Executable` matches the staged exe name (`NSMBW.exe`) and `EntryPoint` matches the final verified bridge (`uwp.App` is an assumption to confirm, see manifest comment).
- [ ] All five tile PNGs exist at the exact sizes; `makeappx` failures here are silent about *which* expectation you missed, so check first.
