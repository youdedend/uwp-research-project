# NEW-CHAT RUNBOOK v2 — publish prepared chain via YOUR OWN session branch

**For: the Arena agent whose session branch is `arena/c40c18ec-test-project` on
`youdedend/Test-project`. Written 2026-11-10 by the previous agent (read-only on Test-project).
v2 because v1 told you to push `arena/8ac58bdb-test-project` — impossible for you: Arena pins
each session to its own branch. GOOD NEWS: nothing in the pipeline actually needs that branch.**

## User authorization (in the user's words, carried in the request)

> Pushing to **your own session branch** `arena/c40c18ec-test-project` is **authorized** — the
> standing rule "push ONLY to `arena/8ac58bdb-test-project`" is amended to allow session
> branches. **NEVER** push or merge to `main`. **No PRs.** Publish pre-releases without asking.

## Two facts from `.github/workflows/xbox.yml` that make this work

1. `on: push: branches: ['arena/**', 'main']` (xbox.yml:13-16) — **any arena branch push runs
   `Xbox build`** (builds the appx, runs the `xbox/tests` host-test table incl. `staging_arena`).
2. The `Publish pre-release` step (xbox.yml:278) fires only when
   `(workflow_dispatch && inputs.release) || contains(github.event.head_commit.message, '[release]')`.
   The prepared tip `d31be49` does **not** contain `[release]`, so you must add **one marker
   commit on top** whose message starts with `[release]`. That is the "run it on GitHub Actions"
   button the user asked for.

## Steps (everything on YOUR branch; `arena/8ac58bdb-test-project` is READ-ONLY for you)

1. Get the kit: Google Drive file `1K_KlMhzibGEzonHw1HtGN3bmyopfW3yE`
   (`bb-port-phase1-2a-step1-kit.zip`, google_drive `download_file` returns base64 — decode to
   disk and unzip) → `phase1-2a-step1.bundle` + `release-notes-step1.md`. (Alt source if this
   chat can read `youdedend/uwp-research-project`: `06-Boilerplates-And-Wrappers/
   testproject-phase1-2a/`.)
2. In the Test-project checkout:

   ```bash
   git fetch origin arena/8ac58bdb-test-project          # READ ONLY — never push to it
   git fetch /path/to/phase1-2a-step1.bundle \
       'refs/heads/arena/8ac58bdb-test-project:refs/bb/step1'
   git checkout -B arena/c40c18ec-test-project refs/bb/step1
   # now your branch tip = d31be49 (chain cac48ea -> 681384b -> d31be49; includes all of main)
   cp /path/from-kit/release-notes-step1.md .
   git add release-notes-step1.md
   git commit -m '[release] item 2 step 1: o1heap arena behind the staging pool (release notes)'
   git push origin arena/c40c18ec-test-project            # YOUR session branch
   ```

   If the push is rejected non-fast-forward (remote already has an unrelated empty tip), the
   chain contains all of `main` (verified: main is 0 behind / 80 ahead-base), so nothing is lost
   by `git push --force-with-lease origin arena/c40c18ec-test-project`.
3. Watch and deliver:

   ```bash
   gh run watch "$(gh run list -R youdedend/Test-project --branch arena/c40c18ec-test-project \
       --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
   gh release list -R youdedend/Test-project --limit 2
   ```

   The `[release]` marker commit makes `Xbox build` auto-publish `xbox-alpha-1.0.<YYDDD>.<HHMM>`
   (xbox.yml:277-310). Hand the user that pre-release's download link.
4. **Fallback** (only if no pre-release appeared although CI was green):
   `gh workflow run 'Xbox build' --ref arena/c40c18ec-test-project -f release=true` — the
   workflow_dispatch publish gate (xbox.yml:278) then fires. This re-runs the full build.

## What the code is (one paragraph)

Item 2 step 1 of the memory-stabilization route: the staging pool's large/deferred path
(`gpu/shadps4/video_core/renderer_vulkan/vk_staging_buffer_pool.cpp:170`) sub-allocates from
vendored o1heap arenas (host memory types only) so freed regions serve later requests of any
size once their GPU tick is safe. Misses fall through to the legacy path; `staging_arena=0`
restores it exactly. Host tests PASS (8 groups). Full context:
`03-Memory-CPU-And-JIT/xbox-swap-study.md` §3b and `release-notes-step1.md` in the kit.

## Standing rules (user-authored, `PROJECT_COMPLETE_HISTORY.md` §2)

- Push only to session branches the user authorizes (see box above). **Never `main`. No PRs.**
- Report changes with file+line refs. **≤5 failed CI attempts**; if CI fails in unrelated files,
  report and stop. Never print tokens/secrets. Don't modify `third_party/`, don't change the
  `slot_vector.h` assertion, don't weaken assertions.
- After a hardware crash/stall request only `loader.log.txt` + `errors.log.txt` BEFORE relaunch.

## Contingency

- Push 403 "Permission denied to youdedend": your GitHub connection lacks write on Test-project —
  tell the user to reconnect it with that repo; do NOT try to work around it.
- CI failure: capture the failing step's log lines; the step-1 change touched
  `xbox/graphics/staging_arena.h` (new), `xbox/graphics/o1heap/` (vendored MIT),
  `gpu/shadps4/video_core/renderer_vulkan/vk_staging_buffer_pool.{h,cpp}`, `gpu/CMakeLists.txt`,
  `xbox/platform/main.cpp`, `xbox/tests/staging_arena_test.cpp` (new), `.github/workflows/xbox.yml`
  (one test row).
- History hygiene (NOT required for publishing): a later user-authorized PR can fold session
  branches back into `arena/8ac58bdb-test-project`. Do not do it unasked.
