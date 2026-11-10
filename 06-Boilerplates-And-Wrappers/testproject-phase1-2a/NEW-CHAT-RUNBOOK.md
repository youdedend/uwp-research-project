# NEW-CHAT RUNBOOK — push prepared commit `d31be49` to `youdedend/Test-project` and publish

**For: the agent in a fresh Arena chat that has GitHub write access to `youdedend/Test-project`
(and ideally `youdedend/uwp-research-project`) plus the google_drive connector.**
**Written: 2026-11-10 by the previous agent, whose session credential was READ-ONLY on
Test-project and could not push. The user asked for this to be finished via GitHub Actions.**

## What is prepared and why

`youdedend/Test-project` branch `arena/8ac58bdb-test-project` on origin is at `cac48ea`.
Two prepared commits fast-forward on top of it (in order):

- `681384b` — "[release] item 2 stage 2a: pre-allocation recovery ladder and pre-merge reclaim"
- `d31be49` — "bbport item 2 step 1 (xbox-swap study): o1heap arena behind the staging pool"

They are shipped as a **git bundle** `phase1-2a-step1.bundle` inside the zip
`bb-port-phase1-2a-step1-kit.zip`. Get the zip from ONE of these two sources:

1. **Google Drive** (preferred if the connector is on): file id `1K_KlMhzibGEzonHw1HtGN3bmyopfW3yE`
   (https://drive.google.com/file/d/1K_KlMhzibGEzonHw1HtGN3bmyopfW3yE/view). Download with the
   google_drive `download_file` tool (it returns base64 for binary — decode to disk), unzip,
   and use `phase1-2a-step1.bundle`.
2. **Research repo** (if this chat can also read `youdedend/uwp-research-project`):
   `06-Boilerplates-And-Wrappers/testproject-phase1-2a/phase1-2a-step1.bundle`.

The zip also contains `release-notes-step1.md` (what the code does + hardware measurement plan)
and `release-2a-step1.ps1` (the user-machine fallback script).

## Exact commands (bash)

```bash
git clone https://github.com/youdedend/Test-project.git /tmp/Test-project
cd /tmp/Test-project
git fetch origin arena/8ac58bdb-test-project
git checkout -B arena/8ac58bdb-test-project origin/arena/8ac58bdb-test-project
git fetch /path/to/phase1-2a-step1.bundle 'refs/heads/arena/8ac58bdb-test-project:refs/bb/step1'
git merge --ff-only refs/bb/step1        # fast-forwards the branch to d31be49
git push origin arena/8ac58bdb-test-project   # THIS push is the "run on GitHub Actions" button
```

The push triggers the **`Xbox build`** workflow automatically (it builds, runs the `xbox/tests`
host-test table including the new `staging_arena` row, and auto-publishes a `[release]`
pre-release named `xbox-alpha-1.0.<YYDDD>.<HHMM>`). Then:

```bash
gh run watch "$(gh run list -R youdedend/Test-project --branch arena/8ac58bdb-test-project --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
gh release list -R youdedend/Test-project --limit 2
```

Report to the user: the workflow run URL, the new pre-release tag + download link, and the
host-test results. That pre-release link is the deliverable.

## Standing rules for Test-project (user-authored, `PROJECT_COMPLETE_HISTORY.md` §2)

- Commit/push **ONLY** to `arena/8ac58bdb-test-project`. **NEVER** push or merge to `main`.
  **No pull request without explicit authorization.** Publishing pre-releases needs no asking
  (the workflow does it).
- Report changes with file+line refs. Run/observe `xbox/tests`. **≤5 failed CI attempts**; if CI
  fails in files unrelated to the change, report and stop.
- Never print tokens/secrets. Don't modify `third_party/`, don't change the `slot_vector.h`
  assertion, don't weaken assertions.
- After a crash/stall on hardware, request only `loader.log.txt` + `errors.log.txt` BEFORE relaunch.

## Contingency

- **`git push` fails 403** ("Permission ... denied to youdedend"): this chat's GitHub connection
  is still read-only for Test-project. Tell the user the GitHub connection needs access to
  `youdedend/Test-project`, or fall back to walking them through `release-2a-step1.ps1` in
  PowerShell on any machine with `git` + `gh` signed in (it does the same steps automatically).
- **CI fails**: capture the failing step's log lines and report; do not blindly re-run more than
  5 times. The new code touched: `xbox/graphics/staging_arena.h` (new), `xbox/graphics/o1heap/`
  (vendored MIT), `gpu/shadps4/video_core/renderer_vulkan/vk_staging_buffer_pool.{h,cpp}`,
  `gpu/CMakeLists.txt`, `xbox/platform/main.cpp`, `xbox/tests/staging_arena_test.cpp` (new),
  `.github/workflows/xbox.yml` (one test row).
- **Bundle refuses to fetch** ("does not contain the prerequisite"): the clone is not at
  `cac48ea`; fetch the branch first (the commands above do).

## What the code does (one paragraph)

Item 2 step 1 of the memory-stabilization route: the staging pool's large/deferred path
(`vk_staging_buffer_pool.cpp:170`) sub-allocates from o1heap arenas (host memory types only)
so freed regions serve later requests of any size once their GPU tick is safe
(`scheduler.IsFree`, never before). Any miss falls through to the legacy dedicated path;
`staging_arena=0` in bbport.ini restores the old behavior exactly. Host tests PASS (8 groups).
Hardware effect is unmeasured until the user runs the regression route on their Xbox — the
measurement plan is in `release-notes-step1.md`.
