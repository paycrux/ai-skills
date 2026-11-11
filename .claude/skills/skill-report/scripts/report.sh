#!/usr/bin/env bash
# Files an ai-skills issue from a brief. A fresh headless agent session (Claude Code or Codex) reads the
# skill source read-only and returns the issue as JSON; this script posts it with gh.
# Usage: report.sh <brief-file>        Agent: $SKILL_REPORT_AGENT (claude|codex), else whichever is installed.
# Last stdout line is the issue (or comment) URL. Non-zero exit = nothing was posted.
set -euo pipefail

REPO="paycrux/ai-skills"
BRIEF="${1:?usage: report.sh <brief-file>}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

[[ -s "$BRIEF" ]] || { echo "skill-report: brief file is empty or missing: $BRIEF" >&2; exit 2; }
AGENT="${SKILL_REPORT_AGENT:-}"
if [[ -z "$AGENT" ]]; then
  if command -v claude >/dev/null; then AGENT=claude; elif command -v codex >/dev/null; then AGENT=codex; fi
fi
[[ "$AGENT" == claude || "$AGENT" == codex ]] || { echo "skill-report: neither 'claude' nor 'codex' CLI found — install one to open a new session" >&2; exit 3; }
command -v "$AGENT" >/dev/null || { echo "skill-report: '$AGENT' CLI not found" >&2; exit 3; }
command -v gh >/dev/null || { echo "skill-report: 'gh' CLI not found" >&2; exit 3; }
command -v python3 >/dev/null || { echo "skill-report: 'python3' not found" >&2; exit 3; }
gh auth status >/dev/null 2>&1 || { echo "skill-report: gh is not logged in — run 'gh auth login'" >&2; exit 3; }

# Source to read the skill from: dev checkout > persistent clone > installed skills dir.
SRC="${AI_SKILLS_REPO:-}"
if [[ -z "$SRC" && -d "$HOME/.ai-skills/repo/.git" ]]; then SRC="$HOME/.ai-skills/repo"; fi
if [[ -z "$SRC" ]]; then SRC="$(cd "$SKILL_DIR/.." && pwd)"; fi

VERSION="unknown"
if git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1; then
  VERSION="$(git -C "$SRC" describe --tags --always 2>/dev/null || echo unknown)"
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
gh issue list -R "$REPO" --state open --limit 50 --json number,title,body \
  | python3 -c '
import json, sys
for i in json.load(sys.stdin):
    body = (i.get("body") or "")[:300].replace("\n", " ")
    print("#%s %s\n  %s" % (i["number"], i["title"], body))' > "$WORK/open-issues.txt"

cat > "$WORK/schema.json" <<'EOF'
{"type": "object", "additionalProperties": false, "required": ["action", "number", "title", "label", "body"],
 "properties": {
  "action": {"type": "string", "enum": ["create", "comment"]},
  "number": {"type": "integer", "description": "the open issue to comment on; 0 when action is create"},
  "title": {"type": "string", "description": "[<skill>] <one-line summary>; empty when action is comment"},
  "label": {"type": "string", "enum": ["bug", "feature update"]},
  "body": {"type": "string", "description": "issue body or comment, Markdown, Korean"}}}
EOF

PROMPT="$(cat <<EOF
You are writing one GitHub issue for ${REPO} from the brief below. You are a fresh session;
the user is not watching and cannot answer questions. You only read files — the caller posts
what you return. Reply with the JSON object the schema asks for and nothing else.

Brief:
$(cat "$BRIEF")

ai-skills version: ${VERSION}
Skill sources: ${SRC} (skills live under .claude/skills/<name>/ or skills/<name>/)
Issue body template: ${SKILL_DIR}/templates/issue-body.md
Open issues on ${REPO} (number, title, start of body):
$(cat "$WORK/open-issues.txt")

Steps:
1. Read the named skill's SKILL.md (and a referenced file if the brief points into it).
   Find the section or rule that produces the reported behavior. If you cannot pin it,
   say "추정" next to the location rather than inventing one.
2. If an open issue above describes the same problem → action "comment", its number, and a
   comment body with the new context.
3. Otherwise → action "create", number 0, title "[<skill>] <one-line summary>", and the body
   written from the template, in Korean.
   Label: "bug" for kind=bug, "feature update" for kind=pain.

Rules:
- ${REPO} is PUBLIC. Remove anything that identifies the user's project or company:
  client/company names, internal URLs, Jira keys, home-directory paths, file contents
  from their app, tokens, emails. Replace with generic descriptions.
- Quote the complaint verbatim; do not soften or exaggerate it.
- No filler words (전반적으로, 개선, 안정성 향상). State what happens, not intent.
EOF
)"

cd "$SRC"
if [[ "$AGENT" == claude ]]; then
  claude -p "$PROMPT" --output-format json --json-schema "$(cat "$WORK/schema.json")" \
    --tools Read Grep Glob --allowedTools Read Grep Glob --permission-mode dontAsk \
    --add-dir "$SKILL_DIR" --no-session-persistence > "$WORK/raw.json"
  python3 - "$WORK/raw.json" "$WORK/out.json" <<'EOF'
import json, sys
data = json.load(open(sys.argv[1]))
if isinstance(data, list):
    data = next((m for m in reversed(data) if m.get("type") == "result"), {})
out = data.get("structured_output")
if data.get("is_error") or not isinstance(out, dict):
    sys.exit("skill-report: the session returned no issue")
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
EOF
else
  codex exec --sandbox read-only --skip-git-repo-check -C "$SRC" \
    --output-schema "$WORK/schema.json" -o "$WORK/out.json" "$PROMPT" < /dev/null > "$WORK/codex.log" 2>&1 \
    || { tail -20 "$WORK/codex.log" >&2; echo "skill-report: codex exec failed" >&2; exit 4; }
fi

python3 - "$WORK/out.json" "$WORK" <<'EOF'
import json, sys
o = json.load(open(sys.argv[1]))
open(f"{sys.argv[2]}/body.md", "w").write(o["body"])
open(f"{sys.argv[2]}/fields", "w").write(f'{o["action"]}\n{o["number"]}\n{o["label"]}\n{o["title"]}\n')
EOF
{ read -r ACTION; read -r NUMBER; read -r LABEL; read -r TITLE; } < "$WORK/fields"

if [[ "$ACTION" == comment && "$NUMBER" -gt 0 ]]; then
  gh issue comment "$NUMBER" -R "$REPO" --body-file "$WORK/body.md"
else
  gh issue create -R "$REPO" --title "$TITLE" --label "$LABEL" --body-file "$WORK/body.md"
fi
