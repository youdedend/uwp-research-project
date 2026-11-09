# uwp-research-project

Xbox UWP porting research (Win32 games → UWP-on-Xbox, Dev Mode). Evidence-based — every
study cites pinned sources and marks verification status. Progress % is only claimed where
committed files back it (per the 2026-11-07 audit rules).

## Research folder map & artifact status (2026-11-07)

| Folder | Status | Artifacts |
|---|---|---|
| `01-Core-Architecture/` | 🟡 in progress | `packaging-and-deployment.md` (appx/Device Portal case study), `bloodborne-xbox-uwp-feasibility.md` (feasibility dossier, amended w/ Test-project field data) |
| `02-Graphics-And-Shaders/` | ⬜ pending | — |
| `03-Memory-CPU-And-JIT/` | 🟡 in progress | `dev-mode-memory-and-system-caps.md` (1/5/128 MB caps, App-vs-Game), `testproject-field-notes.md` (Series S field evidence) |
| `04-Filesystem-Mods-And-Caches/` | ⬜ pending | — |
| `05-Input-And-Audio/` | 🟡 in progress | `input-stack-gameinput-vs-wgi.md`, `audio-notes.md` |
| `06-Boilerplates-And-Wrappers/` | 🟡 in progress | `testproject-phase1-2a/` (item-2 recovery ladder patch + tests for Test-project) |

Chat-only research (Phases 1–2, Blind Spots #1–#4, the progress audit) is **0 %-weighted**
until it lands as files here. Next: graphics/present-chain study, filesystem/mods, the
Dawn-Tint shader pipeline notes, boilerplate wrappers.

## Ground truth pins

- Case-study port: `YTReviveMe/melee-UWP.` (trailing period) branch `UWP-Port`
  (dawn `1155e0ed`, vendored `extern/aurora@5794daa2` = build of record, SDL3-uwp
  `XboxEmulationHub/SDL3-uwp@ec2e0e7c`, nod `encounter/nod@ebd80ca`).
- Xbox Dev Mode caps: memory 1 GB app / 5 GB game / 128 MB background; 2 GB per-file;
  classification toggle in Device Portal. Sources in `03-Memory-CPU-And-JIT/…-caps.md`.
