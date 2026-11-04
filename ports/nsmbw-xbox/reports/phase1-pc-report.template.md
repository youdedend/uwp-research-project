# Phase 1 PC baseline report (template)

Copy this template to `ports\nsmbw-xbox\work\phase1\phase1-manual-report.md`, fill it in, and paste back the completed summary. Do **not** attach the game folder, extracted game files, `work\game`, generated/translated source, saves, certificates, or built packages. The script's `phase1-report.json` and `compile_commands.json` may contain your local username/paths—review or redact them before sharing.

## Run identity

- Date/time started:
- Result: `build-complete-manual-smoke-pending` / `gate-g1-pass` / `failed`
- Command used (redact only personal path components if you wish):
- NSMBW commit shown by bootstrap/audit:
- Total elapsed time:

## PC environment

- Windows edition/build:
- CPU:
- GPU + driver:
- RAM:
- Free disk space before the run:
- Git version:
- Python version (`python --version` or `py -3 --version`):
- .NET SDK (`dotnet --list-sdks`):
- Visual Studio 2022 edition/version (for later phases):

## Automated build checklist

- [ ] Pinned bootstrap/audit passed
- [ ] `Prepare-PortableTools.ps1` completed
- [ ] `Prepare-Dependencies.ps1` completed
- [ ] `unpack_game.py` accepted the folder as `SMNE01` revision 1 / clean `main.dol`
- [ ] `prelink_rels.py` completed and all REL layout checks said `ok`
- [ ] Translator `translate-recursive` completed
- [ ] `emit-base-manifest` completed
- [ ] `generate-data-init` completed
- [ ] `emit-build-shards` completed; `generated\build_shards\shards.cmake` exists
- [ ] CMake configure completed; `native-build\build.ninja` exists
- [ ] `WiiCompiled` build exited `0`; `native-build\WiiCompiled.exe` exists
- [ ] `dsp_coef.bin`, `initial_pipeline_cache.db`, and `wii_bootstrap\` are beside the exe
- [ ] `compile_commands.json` was captured under `work\phase1\`

## Artifact facts from `phase1-report.json`

- Exe size (bytes):
- Exe SHA-256:
- Compile-command entries:
- `compile_commands.json` SHA-256:
- Build elapsed seconds:
- Any `[warn]` checks:

## Manual PC smoke test (Gate G1)

- [ ] Game launches to the title screen
- [ ] World 1-1 completed
- [ ] Save created or updated
- [ ] Exited and relaunched
- [ ] Save is still present after relaunch
- [ ] Audio present and roughly in sync
- [ ] Controller/keyboard input works; note which device was used:
- [ ] No blocking graphical corruption observed

Notes / approximate performance observations (steady-state FPS and shader-compile stalls separately, if noticed):

## If it failed

- Failing step heading printed by the wrapper:
- Exit code shown:
- Relevant log file name (for example `rebuild-translate.log`, `configure.log`, or `rebuild-build.log`):
- Last 30 relevant log lines:

```text
(paste text log lines only—not game files)
```

## Patches 0001-0003 no-behaviour-change rebuild (after G1 passes)

- [ ] Applied `patches/0001-aurora-store-detection.patch`
- [ ] Applied `patches/0002-aurora-uwp-dep-providers.patch`
- [ ] Applied `patches/0003-aurora-extern-link-hygiene.patch`
- [ ] Desktop rebuild exited `0`
- [ ] PC launch/title smoke test still passes
- Desktop rebuild elapsed time:
- Any new warnings/errors attributable to patches `0001`-`0003`:
