#!/usr/bin/env python3
"""Repository-local validation for GitHub Actions and pre-push checks.

This validator intentionally does not need the game, a Windows toolchain, or
network access. It checks the code and templates committed to this research
repository: Python syntax, structured configuration, Markdown links, basic
patch hygiene, the NSMBW source lock, and forbidden generated/copyright game
material outside ignored work directories.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

EXCLUDED_DIRS = {
    '.git',
    '__pycache__',
    '.mypy_cache',
    '.pytest_cache',
    '.venv',
    'node_modules',
    'work',
    'build',
    'build-uwp',
    'obj',
    'obj-deps',
    'staging',
}
TEXT_SUFFIXES = {
    '.json',
    '.md',
    '.ps1',
    '.py',
    '.toml',
    '.txt',
    '.yaml',
    '.yml',
}
FORBIDDEN_SUFFIXES = {
    '.appx',
    '.appxbundle',
    '.cer',
    '.dll',
    '.dol',
    '.elf',
    '.exe',
    '.iso',
    '.msix',
    '.msixbundle',
    '.nand',
    '.pfx',
    '.pvk',
    '.rel',
    '.snk',
    '.wbfs',
}
FORBIDDEN_FILE_NAMES = {
    'compile_commands.json',
    'main.dol',
    'nsmbw_linked.rel',
    'phase1-report.json',
}
FORBIDDEN_DIR_NAMES = {
    'GameAssets',
    'NAND',
    'Saves',
}
FULL_COMMIT_RE = re.compile(r'^[0-9a-f]{40}$')
SHA1_RE = re.compile(r'^[0-9a-f]{40}$')
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')
MARKDOWN_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: Path, message: str) -> None:
        self.errors.append(f'{path}: {message}')

    def require(self, condition: bool, path: Path, message: str) -> None:
        if not condition:
            self.error(path, message)


def iter_files(root: Path):
    for path in sorted(root.rglob('*')):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def rel(root: Path, path: Path) -> Path:
    return path.relative_to(root)


def check_forbidden_files(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        relative = rel(root, path)
        if any(part in FORBIDDEN_DIR_NAMES for part in relative.parts):
            findings.error(relative, 'game/save data directories must stay outside the repository')
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.error(relative, 'binary/package/key/game file must not be committed')
        if path.name in FORBIDDEN_FILE_NAMES:
            findings.error(relative, 'generated local build/game artifact must stay under ignored work/')


def check_text_hygiene(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {'README', 'LICENSE'}:
            continue
        relative = rel(root, path)
        data = path.read_bytes()
        if not data:
            continue
        if not data.endswith(b'\n'):
            findings.error(relative, 'text file must end with a newline')
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as exc:
            findings.error(relative, f'not valid UTF-8: {exc}')
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                findings.error(relative, f'trailing whitespace on line {line_no}')
                break


def check_python_syntax(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        if path.suffix.lower() != '.py':
            continue
        relative = rel(root, path)
        try:
            compile(path.read_text(encoding='utf-8'), str(relative), 'exec')
        except SyntaxError as exc:
            findings.error(relative, f'Python syntax error: {exc}')


def check_structured_files(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        relative = rel(root, path)
        suffix = path.suffix.lower()
        try:
            if suffix == '.json':
                json.loads(path.read_text(encoding='utf-8'))
            elif suffix == '.toml':
                tomllib.loads(path.read_text(encoding='utf-8'))
            elif suffix in {'.xml', '.appxmanifest'}:
                ET.parse(path)
        except Exception as exc:  # report parser class/message as one validation error
            findings.error(relative, f'structured-file parse failed: {exc}')


def check_markdown_links(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        if path.suffix.lower() != '.md':
            continue
        relative = rel(root, path)
        text = path.read_text(encoding='utf-8')
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw = match.group(1).strip()
            if not raw or raw.startswith(('#', 'http://', 'https://', 'mailto:')):
                continue
            if raw.startswith('<') and '>' in raw:
                target = raw[1:raw.index('>')]
            else:
                target = raw.split()[0]
            target = unquote(target.split('#', 1)[0])
            if not target:
                continue
            if not (path.parent / target).resolve().exists():
                findings.error(relative, f'broken relative Markdown link: {raw}')


def check_patch_files(root: Path, files: list[Path], findings: Findings) -> None:
    for path in files:
        if path.suffix.lower() != '.patch':
            continue
        relative = rel(root, path)
        text = path.read_text(encoding='utf-8')
        findings.require('diff --git ' in text, relative, 'patch does not look like a Git diff')
        findings.require('\n@@ ' in text, relative, 'patch has no hunks')
        findings.require('SMNE01' not in text or 'main.dol' not in text.lower(), relative, 'patch unexpectedly references game executable material')


def collect_sha256_values(value: object) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if 'sha256' in key.lower():
                if isinstance(child, str):
                    values.append(child)
                elif isinstance(child, dict):
                    values.extend(str(v) for v in child.values() if isinstance(v, str))
            values.extend(collect_sha256_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(collect_sha256_values(child))
    return values


def check_sources_lock(root: Path, findings: Findings) -> None:
    lock_path = root / 'ports' / 'nsmbw-xbox' / 'sources.lock.json'
    relative = rel(root, lock_path)
    if not lock_path.exists():
        findings.error(relative, 'missing sources.lock.json')
        return

    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    findings.require(lock.get('schema') == 1, relative, 'schema must be 1')
    findings.require(lock.get('project') == 'nsmbw-xbox-series-s', relative, 'unexpected project id')

    target = lock.get('target') or {}
    findings.require(target.get('consoleDeveloperModeConfirmedByUser') is True, relative, 'Series S Developer Mode confirmation missing')

    game = lock.get('requiredGameInput') or {}
    findings.require(game.get('confirmedByUser') is True, relative, 'exact game confirmation missing')
    findings.require(
        SHA1_RE.fullmatch(str(game.get('expectedCleanMainDolSha1CheckedByUpstreamTool', ''))) is not None,
        relative,
        'expected clean main.dol SHA-1 missing or malformed',
    )

    repos = {str(repo.get('id')): repo for repo in lock.get('repositories', [])}
    for repo_id in ('nsmbw', 'retro-rewind-xbox', 'wiicompiled-v0.2.31'):
        repo = repos.get(repo_id)
        findings.require(repo is not None, relative, f'missing pinned repository: {repo_id}')
        if repo is None:
            continue
        findings.require(
            FULL_COMMIT_RE.fullmatch(str(repo.get('commit', ''))) is not None,
            relative,
            f'{repo_id} commit is not a full lowercase Git SHA',
        )
        findings.require(
            str(repo.get('url', '')).startswith('https://github.com/'),
            relative,
            f'{repo_id} URL is not an HTTPS GitHub URL',
        )

    for value in collect_sha256_values(lock):
        findings.require(SHA256_RE.fullmatch(value) is not None, relative, f'malformed SHA-256 value: {value[:16]}...')

    prebuilts = {str(item.get('id')): item for item in lock.get('externalPrebuiltsToVerifyBeforeUse', [])}
    findings.require('uwp-dep-main' in prebuilts, relative, 'missing main UWP dependency pin')
    findings.require('uwp-dep-sdl-true-app' in prebuilts, relative, 'missing separate true-UWP SDL pin')
    if 'uwp-dep-main' in prebuilts and 'uwp-dep-sdl-true-app' in prebuilts:
        findings.require(
            prebuilts['uwp-dep-main'].get('commit') != prebuilts['uwp-dep-sdl-true-app'].get('commit'),
            relative,
            'main UWP bundle and true-UWP SDL must remain separate commits',
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='repository root (default: current directory)')
    args = parser.parse_args()

    root = args.root.resolve()
    findings = Findings()
    files = list(iter_files(root))

    check_forbidden_files(root, files, findings)
    check_text_hygiene(root, files, findings)
    check_python_syntax(root, files, findings)
    check_structured_files(root, files, findings)
    check_markdown_links(root, files, findings)
    check_patch_files(root, files, findings)
    check_sources_lock(root, findings)

    counts = {
        'files': len(files),
        'python': sum(1 for path in files if path.suffix.lower() == '.py'),
        'powershell': sum(1 for path in files if path.suffix.lower() == '.ps1'),
        'markdown': sum(1 for path in files if path.suffix.lower() == '.md'),
    }
    print(
        'repository validation: '
        + ', '.join(f'{key}={value}' for key, value in counts.items())
    )

    if findings.errors:
        print(f'FAILED with {len(findings.errors)} error(s):', file=sys.stderr)
        for error in findings.errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1

    print('repository validation: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
