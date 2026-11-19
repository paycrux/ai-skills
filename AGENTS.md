# Contributing to ai-skills

Rules for working on this repository itself. Unlike `.claude/CLAUDE.md`, which `install.sh` merges
into every user's install, this file is never installed.

## One PR, One Version

Every PR into `main` ships its own version. Users see updates only through `ai-skills version`,
which compares the `VERSION` line in `install.sh` — a PR that leaves it unchanged is invisible.

1. Write the PR's entry under `## [Unreleased]` in `CHANGELOG.md` (Korean, Keep a Changelog sections).
2. Before opening the PR, run `python3 scripts/bump-version.py` — add `--minor` when the rule below says so.
   It computes the next version from `main`, moves the `[Unreleased]` entries under the new
   version header, and updates `install.sh`. Commit both files with the PR.
3. Re-run it after adding more entries or after rebasing onto a `main` that moved; it keeps one
   version for the branch. `python3 scripts/bump-version.py --check` exits 1 when the branch has
   no version of its own.

### Which number

| Bump | When |
|---|---|
| patch (default) | Bug fix, docs, or a behavior change inside an existing skill |
| `--minor` | A skill added or removed, or users must do something different after updating: an install/update step, a document migration (`flow.py migrate`), a command or flag renamed or removed |
| `--major` | Not used while the version is `0.x`; `1.0.0` is a deliberate team decision |

When one PR carries both kinds, the larger bump wins.
