# NEW-CHAT RUNBOOK v3 — publish diag-1 via YOUR OWN session branch

**For: any Arena agent the user sends to publish on `youdedend/Test-project`. Written 2026-11-10
by the research session (read-only on Test-project). v3 supersedes v2 (which published step 1 as
`xbox-alpha-1.0.26314.1455`). The change: the prepared tip now sits on top of `9849caf`, and your
session branch may have ANY `arena/<id>-test-project` name — the publish trick is unchanged.**

## User authorization (in the user's words, carried in the request)

> Pushing to **your own session branch** (`arena/<your-id>-test-project`) is **authorized** — the
> standing rule "push ONLY to `arena/8ac58bdb-test-project`" is amended to allow session
> branches. **NEVER** push or merge to `main`. **No PRs.** Publish pre-releases without asking.

## Two facts from `.github/workflows/xbox.yml` that make this work

1. `on: push: branches: ['arena/**', 'main']` — **any arena branch push runs `Xbox build`**
   (appx + the full `xbox/tests` host-test table).
2. The `Publish pre-release` step fires only when
   `(workflow_dispatch && inputs.release) || contains(github.event.head_commit.message, '[release]')`.
   The prepared tip `eb3ad91` does **not** contain `[release]`, so you add **one marker commit on
   top** whose message starts with `[release]`. That is the "run it on GitHub Actions" button.

## What diag-1 is (do not re-review it deeply; it is pre-tested)

Commit `eb3ad91` "diag-1: staging telemetry row, wedge tags, and copy-mismatch hardening" —
+140 lines over 8 files: (1) the staging memory row (step-1 measurement Q1/Q2), (2) named
stall-report tags on the dense-arena merge copy / texture copies / big buffer-cache allocs,
(3) copy-layer-mismatch hardening (count + poison + refuse). Host tests pass (dense_arena,
arena_admission_policy, recovery_ladder, staging_arena). Details: `release-notes-diag1.md` in
the kit.

## Steps (everything on YOUR branch)

1. Get the kit: Google Drive file **`1cW-nPF8FMYDreuYU6rasfD2P68Y9osj4`**
   (`bb-port-diag1-kit.zip`; google_drive `download_file` streams it to the workspace) →
   unzip → `bb-port-diag1.bundle` + `release-notes-diag1.md`.
2. In your Test-project checkout (your session branch name in the two places marked):

   ```bash
   git fetch origin arena/c40c18ec-test-project   # objects + base 9849caf (READ-ONLY: never push)
   git fetch /path/to/bb-port-diag1.bundle \
       'refs/heads/arena/c40c18ec-test-project:refs/bb/diag1'
   git checkout -B arena/<your-id>-test-project refs/bb/diag1   # tip = eb3ad91 over 9849caf
   cp /path/from-kit/release-notes-diag1.md .
   git add release-notes-diag1.md
   git commit -m '[release] diag-1: staging telemetry, wedge tags, copy-mismatch hardening (release notes)'
   git push origin arena/<your-id>-test-project   # YOUR session branch
   ```

   If the push is rejected non-fast-forward (your remote branch has an unrelated empty tip), the
   chain contains all of `main`, so nothing is lost by
   `git push --force-with-lease origin arena/<your-id>-test-project`.
3. Watch and deliver:

   ```bash
   gh run watch "$(gh run list -R youdedend/Test-project --branch arena/<your-id>-test-project \
       --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
   gh release list -R youdedend/Test-project --limit 2
   ```

   The `[release]` marker makes `Xbox build` auto-publish `xbox-alpha-1.0.<YYDDD>.<HHMM>`.
   Hand the user that pre-release's download link, and report `xbox/tests` results with the
   file+line refs of the changed files (they audit that).
4. **Fallback** (only if no pre-release appeared although CI was green):
   `gh workflow run 'Xbox build' --ref arena/<your-id>-test-project -f release=true`.

## After publishing

Tell the user: the staging row + wedge tags are live; on the next hardware run we want
`loader.log.txt` + `errors.log.txt`, and the run should ideally cover the character-creation →
world-load transition again. Remind them of the optional `DZN_DEBUG=d3d12` line in
`graphics-debug.txt`.
