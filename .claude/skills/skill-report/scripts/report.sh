#!/usr/bin/env bash
# Files an ai-skills issue from a brief, in a fresh headless Claude Code session.
# Usage: report.sh <brief-file>
# Last stdout line is the issue (or comment) URL. Non-zero exit = nothing was posted.
set -euo pipefail

REPO="paycrux/ai-skills"
BRIEF="${1:?usage: report.sh <brief-file>}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

[[ -s "$BRIEF" ]] || { echo "skill-report: brief file is empty or missing: $BRIEF" >&2; exit 2; }
command -v claude >/dev/null || { echo "skill-report: 'claude' CLI not found — install Claude Code to open a new session" >&2; exit 3; }
command -v gh >/dev/null || { echo "skill-report: 'gh' CLI not found" >&2; exit 3; }
gh auth status >/dev/null 2>&1 || { echo "skill-report: gh is not logged in — run 'gh auth login'" >&2; exit 3; }

# Source to read the skill from: dev checkout > persistent clone > installed skills dir.
SRC="${AI_SKILLS_REPO:-}"
if [[ -z "$SRC" && -d "$HOME/.ai-skills/repo/.git" ]]; then SRC="$HOME/.ai-skills/repo"; fi
if [[ -z "$SRC" ]]; then SRC="$(cd "$SKILL_DIR/.." && pwd)"; fi

VERSION="unknown"
if git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1; then
  VERSION="$(git -C "$SRC" describe --tags --always 2>/dev/null || echo unknown)"
fi

PROMPT="$(cat <<EOF
You are filing one GitHub issue on ${REPO} from the brief below. You are a fresh session;
the user is not watching and cannot answer questions. Work, post, and print the URL.

Brief:
$(cat "$BRIEF")

ai-skills version: ${VERSION}
Skill sources: ${SRC} (skills live under .claude/skills/<name>/ or skills/<name>/)
Issue body template: ${SKILL_DIR}/templates/issue-body.md

Steps:
1. Read the named skill's SKILL.md (and a referenced file if the brief points into it).
   Find the section or rule that produces the reported behavior. If you cannot pin it,
   say "추정" next to the location rather than inventing one.
2. Search for duplicates: gh issue list -R ${REPO} --state open --search "<2-3 keywords>" --limit 10.
   If an open issue describes the same problem, add a comment with the new context
   (gh issue comment <n> -R ${REPO} --body-file <file>) instead of opening a new issue.
3. Otherwise write the body from the template, in Korean, and create the issue:
   gh issue create -R ${REPO} --title "[<skill>] <one-line summary>" --label <label> --body-file <file>
   Label: "bug" for kind=bug, "feature update" for kind=pain.
4. Print only the issue or comment URL as the very last line of your reply.

Rules:
- ${REPO} is PUBLIC. Remove anything that identifies the user's project or company:
  client/company names, internal URLs, Jira keys, home-directory paths, file contents
  from their app, tokens, emails. Replace with generic descriptions.
- Quote the complaint verbatim; do not soften or exaggerate it.
- Do not edit any file in the skill sources. Write temp files only under \$TMPDIR.
- No filler words (전반적으로, 개선, 안정성 향상). State what happens, not intent.
EOF
)"

cd "$SRC"
claude -p "$PROMPT" \
  --permission-mode dontAsk \
  --allowedTools "Read" "Grep" "Glob" "Write" "Bash(gh issue:*)" "Bash(mktemp:*)" \
  --add-dir "$SKILL_DIR" "${TMPDIR:-/tmp}"
