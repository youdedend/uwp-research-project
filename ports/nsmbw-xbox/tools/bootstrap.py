#!/usr/bin/env python3
"""Clone the pinned NSMBW Xbox port sources into an ignored work folder.

Default work folder: <this repo>/ports/nsmbw-xbox/work/
Default clones: NSMBW v0.3.1 + jajdp/retro-rewind-xbox.
Add --with-baseline to also clone WiiCompiled v0.2.31 for Aurora comparison.

This script never downloads a game, generated game code, certificates or
prebuilt UWP libraries. It refuses to reuse a checkout at the wrong commit or
with local changes; move such a folder yourself rather than letting a bootstrapper delete work.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def git_out(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def checkout_state(repo: Path, expected: str) -> tuple[str, bool]:
    head = git_out(repo, "rev-parse", "HEAD")
    status = git_out(repo, "status", "--porcelain")
    return head, bool(status)


def clone_pinned(spec: dict[str, Any], dest: Path) -> None:
    url = str(spec["url"])
    ref = str(spec.get("ref") or "")
    commit = str(spec["commit"])

    if dest.exists():
        if not (dest / ".git").exists():
            raise SystemExit(f"refusing to reuse non-git folder: {dest}")
        head, dirty = checkout_state(dest, commit)
        if head.lower() != commit.lower():
            raise SystemExit(
                f"refusing to reuse {dest}: HEAD is {head or 'unknown'}, lock wants {commit}. "
                "Move it aside or choose another --work-dir."
            )
        if dirty:
            raise SystemExit(f"refusing to reuse dirty checkout: {dest} (commit/stash your work first)")
        print(f"already pinned: {dest} @ {commit[:12]}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    if ref.startswith("v") and len(ref) < 32:
        run(["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)])
    else:
        run(["git", "clone", "--filter=blob:none", "--no-checkout", url, str(dest)])
        run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", commit])
        run(["git", "-C", str(dest), "checkout", "--detach", commit])

    head, dirty = checkout_state(dest, commit)
    if head.lower() != commit.lower() or dirty:
        raise SystemExit(f"clone verification failed for {dest}: HEAD={head}, dirty={dirty}")


def main(argv: list[str] | None = None) -> int:
    port_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=port_root / "work", help="where clones live")
    parser.add_argument("--lock", type=Path, default=port_root / "sources.lock.json")
    parser.add_argument("--with-baseline", action="store_true", help="also clone WiiCompiled v0.2.31")
    parser.add_argument("--audit", action="store_true", help="run tools/audit_uwp.py after cloning")
    args = parser.parse_args(argv)

    if shutil.which("git") is None:
        parser.error("git was not found on PATH")
    if not args.lock.exists():
        parser.error(f"missing lock file: {args.lock}")

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    by_id = {str(r["id"]): r for r in lock.get("repositories", [])}
    wanted = ["nsmbw", "retro-rewind-xbox"]
    if args.with_baseline:
        wanted.append("wiicompiled-v0.2.31")

    destinations: dict[str, Path] = {}
    folder_names = {
        "nsmbw": "NSMB-Wii-Multiplayer-Recompilation",
        "retro-rewind-xbox": "retro-rewind-xbox",
        "wiicompiled-v0.2.31": "Wiicompiled-v0.2.31",
    }
    for repo_id in wanted:
        spec = by_id.get(repo_id)
        if spec is None:
            raise SystemExit(f"lock file has no repository id: {repo_id}")
        dest = args.work_dir.resolve() / folder_names[repo_id]
        clone_pinned(spec, dest)
        destinations[repo_id] = dest

    args.work_dir.resolve().mkdir(parents=True, exist_ok=True)
    report = args.work_dir.resolve() / "BOOTSTRAP-REPORT.md"
    lines = [
        "# Bootstrap report (generated, keep under work/)",
        "",
        "Pinned clones prepared by `tools/bootstrap.py`:",
        "",
    ]
    for repo_id, dest in destinations.items():
        lines.append(f"- `{repo_id}` -> `{dest}` @ `{by_id[repo_id]['commit']}`")
    lines += [
        "",
        "Next commands (PowerShell, from the repository root):",
        "",
        "```powershell",
        "python ports/nsmbw-xbox/tools/audit_uwp.py `",
        f"  --nsmbw \"{destinations['nsmbw']}\" `",
        f"  --recipe \"{destinations['retro-rewind-xbox']}\" `",
        "  --out ports/nsmbw-xbox/reports/phase0-audit-local.md --check",
        "```",
        "",
        "No game files, generated game code, UWP prebuilts or certificates were downloaded.",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report}")

    if args.audit:
        audit = port_root / "tools" / "audit_uwp.py"
        cmd = [
            sys.executable,
            str(audit),
            "--nsmbw",
            str(destinations["nsmbw"]),
            "--recipe",
            str(destinations["retro-rewind-xbox"]),
            "--check",
            "--out",
            str(args.work_dir.resolve() / "phase0-audit.md"),
        ]
        baseline = destinations.get("wiicompiled-v0.2.31")
        if baseline is not None:
            cmd += ["--wiicompiled-v0231", str(baseline)]
        run(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
