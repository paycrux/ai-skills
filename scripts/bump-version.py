#!/usr/bin/env python3
"""Give the current branch its own release: one PR = one version.

    python3 scripts/bump-version.py            # patch: 0.13.7 -> 0.13.8
    python3 scripts/bump-version.py --minor    # 0.13.7 -> 0.14.0
    python3 scripts/bump-version.py --check    # exit 1 if this branch has no version of its own

The next version is computed from the base branch's install.sh, not the local one, so the
script can be re-run after a rebase. The entries under `## [Unreleased]` in CHANGELOG.md become
`## [<new>] - <today>`; if this branch already released them, that header is renamed instead.
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = re.compile(r'^VERSION="(\d+)\.(\d+)\.(\d+)"', re.M)
HEADER_RE = re.compile(r"^## \[([^\]]+)\]", re.M)


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def parse_version(text, where):
    m = VERSION_RE.search(text)
    if not m:
        sys.exit(f'No VERSION="x.y.z" line in {where}')
    return tuple(int(x) for x in m.groups())


def fmt(v):
    return ".".join(str(x) for x in v)


def base_file(base, path):
    """Read a file from origin/<base>, falling back to the local <base> branch when offline."""
    if git("fetch", "--quiet", "origin", base, check=False).returncode != 0:
        print(f"warning: could not fetch origin/{base}; using the local ref", file=sys.stderr)
    for ref in (f"origin/{base}", base):
        r = git("show", f"{ref}:{path}", check=False)
        if r.returncode == 0:
            return r.stdout
    sys.exit(f"Cannot read {path} from origin/{base} or {base}")


def parse_sections(body):
    """'### Added' blocks -> [(title, [item lines])]; nested '  - ' lines stay with their item."""
    sections = []
    for line in body.split("\n"):
        if line.startswith("### "):
            sections.append((line[4:].strip(), []))
        elif line.strip() and sections:
            sections[-1][1].append(line)
    return [s for s in sections if s[1]]


def merge(base, extra):
    out = [(title, list(items)) for title, items in base]
    for title, items in extra:
        for existing_title, existing_items in out:
            if existing_title == title:
                existing_items.extend(items)
                break
        else:
            out.append((title, list(items)))
    rank = {t: i for i, t in enumerate(["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"])}
    return sorted(out, key=lambda s: rank.get(s[0], len(rank)))


def render(header, sections):
    parts = [header, ""]
    for title, items in sections:
        parts += [f"### {title}", ""] + items + [""]
    return "\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    level = ap.add_mutually_exclusive_group()
    level.add_argument("--minor", action="store_true")
    level.add_argument("--major", action="store_true")
    ap.add_argument("--base", default="main", help="branch the PR merges into (default: main)")
    ap.add_argument("--check", action="store_true", help="only verify; change nothing")
    args = ap.parse_args()

    root = Path(git("rev-parse", "--show-toplevel").stdout.strip())
    install_sh = root / "install.sh"
    changelog = root / "CHANGELOG.md"

    base_ver = parse_version(base_file(args.base, "install.sh"), f"{args.base}:install.sh")
    base_headers = set(HEADER_RE.findall(base_file(args.base, "CHANGELOG.md")))
    local_sh = install_sh.read_text(encoding="utf-8")
    local_ver = parse_version(local_sh, "install.sh")
    log = changelog.read_text(encoding="utf-8")

    if args.check:
        if local_ver <= base_ver:
            sys.exit(f"install.sh VERSION {fmt(local_ver)} is not above {args.base} ({fmt(base_ver)}). "
                     "Run: python3 scripts/bump-version.py")
        if f"## [{fmt(local_ver)}]" not in log:
            sys.exit(f"CHANGELOG.md has no ## [{fmt(local_ver)}] section")
        print(f"ok: {fmt(base_ver)} -> {fmt(local_ver)}")
        return

    if args.major:
        new = (base_ver[0] + 1, 0, 0)
    elif args.minor:
        new = (base_ver[0], base_ver[1] + 1, 0)
    else:
        new = (base_ver[0], base_ver[1], base_ver[2] + 1)
    new_header = f"## [{fmt(new)}] - {datetime.date.today().isoformat()}"

    unreleased = re.search(r"^## \[Unreleased\]\n(.*?)(?=^## \[)", log, re.M | re.S)
    if not unreleased:
        sys.exit("CHANGELOG.md has no ## [Unreleased] section followed by a release")

    pending = parse_sections(unreleased.group(1))
    top = HEADER_RE.search(log, unreleased.end())
    own = top is not None and top.group(1) not in base_headers  # this branch already released once

    if own:
        own_end = HEADER_RE.search(log, top.end())
        own_end = own_end.start() if own_end else len(log)
        sections = merge(parse_sections(log[log.index("\n", top.start()):own_end]), pending)
        log = log[:unreleased.start()] + "## [Unreleased]\n\n" + render(new_header, sections) + log[own_end:]
    elif pending:
        log = log[:unreleased.start()] + "## [Unreleased]\n\n" + render(new_header, pending) + log[unreleased.end():]
    else:
        sys.exit("No entry for this PR: write it under ## [Unreleased] in CHANGELOG.md, then re-run.\n"
                 "(After a rebase conflict, move this branch's entries back under ## [Unreleased] first.)")

    changelog.write_text(log, encoding="utf-8")
    install_sh.write_text(VERSION_RE.sub(f'VERSION="{fmt(new)}"', local_sh, count=1), encoding="utf-8")
    print(f"{fmt(base_ver)} -> {fmt(new)}  (install.sh, CHANGELOG.md)")


if __name__ == "__main__":
    main()
