#!/usr/bin/env python3
"""Phase-0 UWP audit for the NSMBW Xbox Series S port.

This tool is deliberately read-only. It verifies pinned commits, dry-runs the
Mario Kart Wii Aurora patch, inventories desktop-only API families in the
NSMBW tree, and writes a Markdown or JSON report containing file names, line
numbers and API symbols only (never quoted source lines).

Examples (PowerShell or bash):
  python tools/audit_uwp.py --nsmbw C:\\src\\NSMB-Wii-Multiplayer-Recompilation \
      --recipe C:\\src\\retro-rewind-xbox --out reports\\phase0-audit.md

  python tools/audit_uwp.py --nsmbw /tmp/nsmbw --recipe /tmp/retro-rewind-xbox \
      --wiicompiled-v0231 /tmp/wiicompiled-v0231 --format json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inl", ".inc",
    ".cmake", ".txt", ".ps1", ".py", ".sh", ".cmd", ".bat", ".toml",
}
SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", "build", "build-uwp", "out"}

# Category -> (human label, regex, porting note). Patterns match symbol names,
# not whole source lines; reports intentionally avoid reproducing source text.
CATEGORIES: dict[str, tuple[str, str, str]] = {
    "known_folders": (
        "Desktop known-folder paths",
        r"SHGetKnownFolderPath|FOLDERID_(?:Documents|LocalAppData|RoamingAppData)",
        "Replace with package LocalState via the UWP-built SDL_GetPrefPath under the port define.",
    ),
    "message_boxes": (
        "Desktop message boxes and fatal popups",
        r"MessageBox[AW]?\(|SDL_ShowSimpleMessageBox|SDL_ShowMessageBox",
        "Console has no desktop popup audience: log to LocalState and fail closed / show an in-game error later.",
    ),
    "console_pipes": (
        "Console transcript / CRT pipes",
        r"_pipe\(|AllocConsole|AttachConsole|CreateNamedPipe|discord-ipc",
        "UWP CRT/AppContainer has no console or desktop named pipes: redirect stdout/stderr to a LocalState file first.",
    ),
    "dbghelp": (
        "DbgHelp symbolication",
        r"DbgHelp|SymInitialize|SymFromAddr|StackWalk64|MiniDumpWriteDump",
        "Keep a log-first crash path; do not make first boot depend on desktop symbol services.",
    ),
    "fibers": (
        "Win32 fibers (plain variants)",
        r"ConvertThreadToFiber\(|CreateFiber\(|SwitchToFiber\(|DeleteFiber\(",
        "The proven recipe switches the App-family-visible calls to the Ex variants; verify declarations in the Store SDK headers.",
    ),
    "vectored_exceptions": (
        "Vectored exception handlers",
        r"AddVectoredExceptionHandler|RemoveVectoredExceptionHandler|RtlAddFunctionTable",
        "Guest-memory traps may need hand declarations even where kernel32 exports the functions; keep this isolated and test on hardware early.",
    ),
    "process_spawn": (
        "Child processes / relaunch / updater process control",
        r"CreateProcess[AW]?\(|ShellExecute[AW]?\(|WinExec\(|posix_spawnp|popen\(",
        "Exclude updater, netplay relaunch and CPU-compat handoff from the first couch-only package instead of porting them.",
    ),
    "desktop_http_tls": (
        "WinHTTP / Schannel / desktop TLS assumptions",
        r"WinHttp[A-Z]|AcquireCredentialsHandle[AW]?\(|InitializeSecurityContext[AW]?\(|EncryptMessage\(|DecryptMessage\(|SCH_CRED_",
        "First package is offline/couch-only: stub guest TLS like the recipe, and omit the self-updater entirely.",
    ),
    "file_pickers": (
        "COM shell file/folder pickers",
        r"IFileOpenDialog|CLSID_FileOpenDialog|CoCreateInstance\(",
        "No desktop folder picker on Xbox: v1 uses a fixed LocalState\\GameAssets\\DATA contract uploaded through Device Portal.",
    ),
    "hwnd_hooks": (
        "HWND / Win32 window-procedure hooks",
        r"HWND|WNDPROC|SetWindowLongPtr|CallWindowProc|GetClientRect|SDL_PROP_WINDOW_WIN32_HWND_POINTER",
        "UWP SDL gives a CoreWindow, not an HWND: guard desktop hooks out and hand Dawn the CoreWindow surface.",
    ),
    "environment": (
        "Environment-variable feature switches",
        r"GetEnvironmentVariable[AW]?\(|std::getenv\(|SDL_getenv\(",
        "Inventory only: preserve harmless reads, but do not let required Xbox configuration depend on desktop environment variables.",
    ),
    "stdext": (
        "MSVC-only stdext iterators",
        r"stdext::",
        "The Store compile pass is expected to use clang with the MSVC ABI; replace or guard these like the recipe's Crypto++ fix.",
    ),
    "sdl_haptics": (
        "SDL haptics initialization",
        r"SDL_INIT_HAPTIC",
        "The recipe's UWP SDL build is used without haptics at init; rumble returns only after the chosen SDL fork proves it.",
    ),
}

POSITIVE_CHECKS: dict[str, tuple[str, str]] = {
    "runtime_main_seam": (
        r"RuntimeMain\s*\(",
        "RuntimeMain(argc, argv) seam exists separately from main(), so a WinRT/SDL entry shim does not need to fork the whole startup path.",
    ),
    "sdl_pref_path": (
        r"SDL_GetPrefPath\s*\(",
        "SDL_GetPrefPath is already used somewhere in the tree; reuse that idiom for LocalState instead of inventing a second path system.",
    ),
    "d3d_backends": (
        r"BACKEND_D3D(?:11|12)|\"d3d(?:11|12)\"",
        "Aurora/runtime already name D3D11/D3D12 backends; Xbox work is surface/package integration, not a renderer rewrite.",
    ),
    "host_suspend_file": (
        r"host_suspend",
        "A host-suspend module name is present; audit it before promising Home/resume behavior (the recipe does not solve Dev Mode suspension).",
    ),
}


def run_git(repo: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def git_head(repo: Path) -> str | None:
    rc, out, _ = run_git(repo, "rev-parse", "HEAD")
    return out if rc == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", out) else None


def git_dirty(repo: Path) -> bool | None:
    rc, out, _ = run_git(repo, "status", "--porcelain")
    if rc != 0:
        return None
    return bool(out)


def load_lock(path: Path | None) -> dict[str, Any]:
    if path is None:
        candidate = Path(__file__).resolve().parents[1] / "sources.lock.json"
        path = candidate if candidate.exists() else None
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def expected_commit(lock: dict[str, Any], repo_id: str) -> str | None:
    for repo in lock.get("repositories", []):
        if repo.get("id") == repo_id:
            value = repo.get("commit")
            return value if isinstance(value, str) else None
    return None


def iter_text_files(root: Path, include_third_party: bool) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & SKIP_DIRS:
            continue
        if not include_third_party and "third_party" in rel_parts:
            continue
        if path.name == "CMakeLists.txt" or path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def scan_tree(root: Path, include_third_party: bool, max_files_per_category: int) -> dict[str, Any]:
    compiled = {key: re.compile(pattern) for key, (_, pattern, _) in CATEGORIES.items()}
    positives = {key: re.compile(pattern) for key, (pattern, _) in POSITIVE_CHECKS.items()}
    hit_counts: Counter[str] = Counter()
    files_by_category: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    positive_hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scanned = 0

    for path in iter_text_files(root, include_third_party):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for key, regex in compiled.items():
                if regex.search(line):
                    hit_counts[key] += 1
                    lines = files_by_category[key][rel]
                    if len(lines) < 8:
                        lines.append(lineno)
            for key, regex in positives.items():
                if regex.search(line) and len(positive_hits[key]) < 6:
                    positive_hits[key].append({"file": rel, "line": lineno})

    if not include_third_party:
        # The one third-party category that blocked the proven recipe's Store
        # compile (Crypto++'s MSVC-only stdext iterators) is always inventoried,
        # even though the full third-party tree is otherwise out of scope here.
        stdext_re = compiled["stdext"]
        for third_party_root in sorted(root.glob("*/third_party")):
            for path in iter_text_files(third_party_root, include_third_party=True):
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                rel = path.relative_to(root).as_posix()
                for lineno, line in enumerate(text.splitlines(), 1):
                    if stdext_re.search(line):
                        hit_counts["stdext"] += 1
                        lines = files_by_category["stdext"][rel]
                        if len(lines) < 8:
                            lines.append(lineno)

    categories: dict[str, Any] = {}
    for key, (label, _pattern, note) in CATEGORIES.items():
        file_map = files_by_category.get(key, {})
        shown = [
            {"file": name, "lines": lines}
            for name, lines in sorted(file_map.items())[:max_files_per_category]
        ]
        categories[key] = {
            "label": label,
            "hits": int(hit_counts[key]),
            "files": len(file_map),
            "examples": shown,
            "note": note,
        }
    return {"filesScanned": scanned, "categories": categories, "positives": dict(positive_hits)}


def parse_patch_stats(patch: Path) -> dict[str, Any]:
    files: list[dict[str, int | str]] = []
    current: dict[str, int | str] | None = None
    for line in patch.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("diff --git "):
            if current is not None:
                files.append(current)
            target = line.split(" b/", 1)[-1]
            current = {"file": target, "hunks": 0, "insertions": 0, "deletions": 0}
        elif current is not None and line.startswith("@@"):
            current["hunks"] = int(current["hunks"]) + 1
        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            current["insertions"] = int(current["insertions"]) + 1
        elif current is not None and line.startswith("-") and not line.startswith("---"):
            current["deletions"] = int(current["deletions"]) + 1
    if current is not None:
        files.append(current)
    return {
        "path": str(patch),
        "filesTouched": len(files),
        "hunks": sum(int(f["hunks"]) for f in files),
        "insertions": sum(int(f["insertions"]) for f in files),
        "deletions": sum(int(f["deletions"]) for f in files),
        "files": files,
    }


def dry_run_patch(nsmbw: Path, patch: Path) -> dict[str, Any]:
    rc, out, err = run_git(
        nsmbw, "apply", "--check", "--directory=aurora-main", str(patch)
    )
    failed: list[str] = []
    for line in (err + "\n" + out).splitlines():
        match = re.search(r"aurora-main/(.+?)(?::\d+)?(?::\s|$)", line)
        if match and ("patch failed" in line or "No such file" in line or "does not apply" in line):
            name = match.group(1).strip()
            if name not in failed:
                failed.append(name)
    return {"returnCode": rc, "appliesCleanly": rc == 0, "failedFiles": failed}


def read_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def seven_change_anchor_status(aurora: Path) -> list[dict[str, str]]:
    """Check the recipe's seven later Aurora changes by short API markers.

    `guarded` is a heuristic: the file already mentions AURORA_WINDOWS_STORE.
    This avoids embedding the recipe script's replacement code in our report.
    """
    checks = [
        ("lib/logging.cpp", "MessageBoxA", "fatal popup must be Store-guarded"),
        ("lib/window.cpp", "WNDPROC g_prevWindowProc", "Win32 window-proc state must be Store-guarded"),
        ("lib/window.cpp", "g_nativeClientSize.load", "native-client-size fast path must be Store-guarded"),
        ("lib/window.cpp", "install_window_proc_hook();", "hook installation must be Store-guarded"),
        ("lib/window.cpp", "uninstall_window_proc_hook();", "hook removal must be Store-guarded"),
        (
            "lib/dawn/BackendBinding.cpp",
            "SurfaceSourceWindowsHWND",
            "add the CoreWindow surface branch before the HWND branch",
        ),
        ("lib/input.cpp", "SDL_INIT_HAPTIC", "Store build initializes input without haptics"),
    ]
    results: list[dict[str, str]] = []
    for rel, marker, action in checks:
        text = read_if_exists(aurora / rel)
        if not text:
            status = "missing-file"
        elif marker not in text:
            status = "anchor-not-found"
        elif "AURORA_WINDOWS_STORE" in text:
            status = "anchor-present-store-symbol-present-review-manually"
        else:
            status = "anchor-present-not-yet-store-guarded"
        results.append({"file": rel, "marker": marker, "status": status, "action": action})
    return results


def aurora_path_diff_count(left: Path, right: Path) -> dict[str, Any] | None:
    if not left.exists() or not right.exists():
        return None
    proc = subprocess.run(
        ["diff", "-qr", str(left), str(right)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    names = [line for line in proc.stdout.splitlines() if line.strip()]
    differing = [line for line in names if "/.git" not in line]
    return {"differingPaths": len(differing), "sample": differing[:25]}


def markdown_report(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# NSMBW Xbox — Phase 0 UWP audit")
    lines.append("")
    lines.append("Generated by `tools/audit_uwp.py`. The tool is read-only; `git apply --check` does not modify the tree.")
    lines.append("")
    lines.append("## Pinned checkouts")
    lines.append("")
    lines.append("| Tree | HEAD | Expected | Dirty? | Verdict |")
    lines.append("|---|---|---|---|---|")
    for name, info in data["checkouts"].items():
        expected = info.get("expected") or "—"
        head = info.get("head") or "not a git checkout"
        verdict = "match" if info.get("matchesExpected") else ("unpinned" if not info.get("expected") else "MISMATCH")
        dirty = "unknown" if info.get("dirty") is None else ("yes" if info.get("dirty") else "no")
        lines.append(f"| {name} | `{head}` | `{expected}` | {dirty} | {verdict} |")
    lines.append("")

    patch = data.get("recipePatch")
    if patch:
        stats = patch["stats"]
        check = patch["dryRun"]
        lines.append("## Recipe Aurora patch")
        lines.append("")
        lines.append(
            f"- Files touched: **{stats['filesTouched']}**; hunks: **{stats['hunks']}**; "
            f"insertions/deletions: **+{stats['insertions']} / -{stats['deletions']}**."
        )
        lines.append(f"- Dry-run against NSMBW: **{'applies cleanly' if check['appliesCleanly'] else 'does not apply cleanly'}** (git exit {check['returnCode']}).")
        if check["failedFiles"]:
            lines.append("- Failed files:")
            for name in check["failedFiles"]:
                lines.append(f"  - `aurora-main/{name}`")
        lines.append("")
        lines.append("| Aurora file | Hunks | + | - |")
        lines.append("|---|---:|---:|---:|")
        for item in stats["files"]:
            lines.append(f"| `{item['file']}` | {item['hunks']} | {item['insertions']} | {item['deletions']} |")
        lines.append("")

    lines.append("## Seven later Aurora changes (anchor check)")
    lines.append("")
    lines.append("| File | Marker | Status | Action |")
    lines.append("|---|---|---|---|")
    for item in data["sevenChangeAnchors"]:
        lines.append(f"| `aurora-main/{item['file']}` | `{item['marker']}` | {item['status']} | {item['action']} |")
    lines.append("")

    scan = data["scan"]
    lines.append("## Desktop-API inventory (NSMBW tree)")
    lines.append("")
    scope = "including third-party trees" if scan.get("thirdPartyFullyScanned") else "excluding third-party trees, except the always-on `stdext` check"
    lines.append(f"Text files scanned: **{scan['filesScanned']}** ({scope}). Counts are symbol-name hits, not a claim that every hit is compiled into the Xbox target.")
    lines.append("")
    lines.append("| Category | Hits | Files | Porting note |")
    lines.append("|---|---:|---:|---|")
    for key in CATEGORIES:
        item = scan["categories"][key]
        lines.append(f"| {item['label']} | {item['hits']} | {item['files']} | {item['note']} |")
    lines.append("")
    for key in CATEGORIES:
        item = scan["categories"][key]
        if not item["examples"]:
            continue
        lines.append(f"### {item['label']}")
        lines.append("")
        for ex in item["examples"]:
            nums = ", ".join(str(n) for n in ex["lines"])
            lines.append(f"- `{ex['file']}` — lines {nums}")
        lines.append("")

    lines.append("## Positive seams already present")
    lines.append("")
    for key, (_pattern, note) in POSITIVE_CHECKS.items():
        hits = scan["positives"].get(key, [])
        lines.append(f"- **{key}**: {note}")
        for hit in hits[:3]:
            lines.append(f"  - `{hit['file']}:{hit['line']}`")
    lines.append("")

    diff = data.get("auroraBaselineDiff")
    if diff:
        lines.append("## Aurora baseline distance")
        lines.append("")
        lines.append(f"Name-only differing paths versus the supplied WiiCompiled baseline: **{diff['differingPaths']}**.")
        lines.append("This is a distance signal only; it does not say which side is newer for any individual file.")
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Do **not** force the recipe patch. Re-implement its provider/surface/path changes semantically on NSMBW's Aurora, behind the same `AURORA_WINDOWS_STORE` boundary.")
    lines.append("- First Xbox package stays couch-only/offline: exclude updater, folder picker, Discord and process-relaunch netplay paths rather than porting them.")
    lines.append("- First runtime change remains observability: early stdout/stderr redirection into `LocalState`, before graphics debugging.")
    lines.append("- A clean audit is not a build. Phase 1 still requires a working, user-supplied-game PC build and its `compile_commands.json`.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nsmbw", required=True, type=Path, help="NSMBW checkout root")
    parser.add_argument("--recipe", type=Path, help="jajdp/retro-rewind-xbox checkout root")
    parser.add_argument("--wiicompiled-v0231", type=Path, help="optional WiiCompiled v0.2.31 checkout root")
    parser.add_argument("--lock", type=Path, help="sources.lock.json (defaults beside this port folder)")
    parser.add_argument("--out", type=Path, help="write report here instead of stdout")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--include-third-party", action="store_true", help="also scan third_party trees (larger report)")
    parser.add_argument("--max-files-per-category", type=int, default=20)
    parser.add_argument("--check", action="store_true", help="exit 2 if a supplied pinned checkout mismatches the lock")
    args = parser.parse_args(argv)

    nsmbw = args.nsmbw.resolve()
    if not (nsmbw / "aurora-main").is_dir() or not (nsmbw / "runtime").is_dir():
        parser.error(f"--nsmbw is not an NSMBW checkout (missing aurora-main/ or runtime/): {nsmbw}")

    lock = load_lock(args.lock)
    checkouts: dict[str, Any] = {}

    def add_checkout(name: str, path: Path | None, lock_id: str) -> None:
        if path is None:
            return
        resolved = path.resolve()
        head = git_head(resolved) if resolved.exists() else None
        expected = expected_commit(lock, lock_id)
        checkouts[name] = {
            "path": str(resolved),
            "head": head,
            "expected": expected,
            "matchesExpected": bool(head and expected and head.lower() == expected.lower()),
            "dirty": git_dirty(resolved) if resolved.exists() else None,
        }

    add_checkout("nsmbw", nsmbw, "nsmbw")
    add_checkout("retro-rewind-xbox", args.recipe, "retro-rewind-xbox")
    add_checkout("wiicompiled-v0.2.31", args.wiicompiled_v0231, "wiicompiled-v0.2.31")

    data: dict[str, Any] = {
        "checkouts": checkouts,
        "scan": scan_tree(nsmbw, args.include_third_party, args.max_files_per_category),
        "sevenChangeAnchors": seven_change_anchor_status(nsmbw / "aurora-main"),
    }

    if args.recipe is not None:
        patch = (args.recipe.resolve() / "patches" / "aurora-uwp.patch")
        if patch.exists():
            data["recipePatch"] = {
                "stats": parse_patch_stats(patch),
                "dryRun": dry_run_patch(nsmbw, patch),
            }

    if args.wiicompiled_v0231 is not None:
        baseline_aurora = args.wiicompiled_v0231.resolve() / "aurora-main"
        data["auroraBaselineDiff"] = aurora_path_diff_count(baseline_aurora, nsmbw / "aurora-main")

    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else markdown_report(data)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered)

    if args.check:
        bad = [name for name, info in checkouts.items() if info.get("expected") and not info.get("matchesExpected")]
        if bad:
            print(f"pinned checkout mismatch: {', '.join(bad)}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
