# RUNBOOK v8 — publish **diag-6** (the publish path this session cannot walk)

Written 2026-11-11 by the research session. v8 supersedes v7 (diag-5, **already published** — by
another session as `f26348e`, build `1.0.26314.2323`). Read §0 first.

## 0. This session cannot write to `Test-project`

Every write path returns 403 for this token (the installation is read-only on `Test-project`,
read-write on `uwp-research-project`):

```
git push                 -> Permission to youdedend/Test-project.git denied to youdedend
POST /git/refs           -> Resource not accessible by integration
PUT  /repos/.../contents -> Resource not accessible by integration
```

So diag-6 is handed over as a kit. **Do not retry the push.**

## What diag-6 is, and why it exists

Base commit **`f26348e619062c240eac41265d758c2254c7dce0`** (diag-5, published as `2323`).
Kit: Drive **`bb-port-diag6-kit.zip` = `1KQ1kDExHWqBhxl-UQyCFXr_tCrMnxlA_`** — `bb-port-diag6.bundle`
(base `f26348e…`), `diag6.patch`, `release-notes-diag6.md`. Verified by fetching the bundle into a
fresh clone (`514def9`, 5 files, +155).

Two diagnostics, no behaviour change:

1. **`ObtainBuffer` now names the addresses it refuses.** It has always rejected a guest address
   outside the 40-bit space and returned the zero buffer — silently. `2323` therefore faulted at
   `0x23FB16ED5BC` (1,279 GiB past guest space, on the recording thread) with nothing in the log
   saying an address had already been rejected. Now: once per distinct address, max 16 per run.
2. **The watchdog explains a declined exit.** It correctly refuses to exit on a stall when there is
   memory to spare (the exit needs *both* 10 s stuck *and* headroom ≤ 150 MiB), and both recent runs
   had ~660 MiB free — but the log could not be distinguished from a dead watchdog. One line per
   stall now says so. 8 new checks in `xbox/tests/watchdog_policy_test.cpp`; **all 65 pass on the
   host** (`g++ -std=c++20 -I xbox/platform xbox/tests/watchdog_policy_test.cpp`).

Known-untouched: the stall itself, and the fault. This build instruments, it does not fix.

## Steps (on YOUR session branch)

```bash
git fetch origin arena/c40c18ec-test-project                  # objects (READ-ONLY)
git fetch /path/to/bb-port-diag6.bundle 'refs/heads/arena/diag6:refs/bb/diag6'
git checkout -B arena/<your-id>-test-project refs/bb/diag6    # tip = 514def9 over f26348e
git log --oneline -3      # expect: 514def9, 4909b75, f26348e
git push origin arena/<your-id>-test-project                  # YOUR branch; NEVER main
```

Patch fallback (applies to `f26348e` exactly):

```bash
git checkout -B arena/<your-id>-test-project f26348e619062c240eac41265d758c2254c7dce0
git apply /path/to/diag6.patch && git add -A
git commit -m '[release] diag-6: report the addresses we refuse, and why the watchdog declined its exit'
git push origin arena/<your-id>-test-project
```

Then watch the run, hand over the pre-release link **and its version string**, and report the
`xbox/tests` table with file+line refs for the four changed files.

## What to ask the user for

Run defaults — **no `dzn_debug`** (the layer is what cost 6 fps; with it off the same build reached
2,577 presents at ~25 fps with a correct picture). Then: `loader.log.txt` + `errors.log.txt`, and
`dozen.log` only if it is bigger than 150 bytes.

Read, in this order:

1. **`ObtainBuffer refused`** — the first such line names the bad address *before* the fault. That is
   the whole point of this build.
2. **`no clean exit at a N s stall`** — confirms the stall's length without a second run.
3. the fault line: it always carries `module=` and `base=` now.
