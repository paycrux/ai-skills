---
name: skill-report
description: "File a bug or a pain point in an ai-skills skill as a GitHub issue on paycrux/ai-skills, from a separate fresh session so the user's working session stays clean. Use when the user, mid-task, complains about a skill or asks to report it — \"flow 이 부분 불편해\", \"이거 버그 같아, 이슈로 올려줘\", \"스킬 리포트\", \"/skill-report\"."
argument-hint: "[skill-name] [what was wrong or inconvenient]"
allowed-tools: Bash, Write
---

# /skill-report — Report an ai-skills bug or pain point as a GitHub issue

The user is in the middle of other work. This skill must not turn the current session
into a reporting session: it writes a short brief, hands it to a **new headless agent
session** (`claude -p` or `codex exec`, read-only), and goes back to the user's task. The new
session reads the skill source, checks the open issues for a duplicate and writes the issue;
the script posts it with `gh`. The current session only sees one line back — the issue URL.

This works the same from Claude Code, Cursor and Codex. The script uses whichever of `claude`
and `codex` is installed (`claude` first); `SKILL_REPORT_AGENT=codex` picks one.

## Step 1: Write the brief (current session — keep it short)

Fill in from what the user said and what just happened. Do not open skill files, search
issues or draft the issue here — that is the new session's job.

| Field | Content |
|---|---|
| `skill` | The skill name (`flow`, `git-pr`, ...). If the user did not name one, infer from the conversation; if two are plausible, ask once. |
| `kind` | `bug` (wrong result, error, crash) or `pain` (works, but inconvenient / slow / confusing) |
| `complaint` | The user's own words, verbatim. Never paraphrase. |
| `context` | 2–5 lines: what step or command was running, what happened, what was expected. Include the exact error text if short. |

**Privacy — the issue tracker is public.** The brief must not carry anything from the
user's project: company or client names, internal URLs, Jira keys, file contents, paths
under the user's home, tokens, emails. Describe the situation generically ("a PRD with 3
Jira stories", "a Next.js app repo"). The new session scrubs again, but do not rely on it.

Write the brief to a temp file:

```bash
BRIEF="$(mktemp -t skill-report).md"
cat > "$BRIEF" <<'EOF'
skill: flow
kind: pain
complaint: <verbatim user words>
context:
- <step/command that was running>
- <what happened / what was expected>
EOF
```

## Step 2: Launch the new session

```bash
bash "<skill>/scripts/report.sh" "$BRIEF"
```

`<skill>` is the folder this `SKILL.md` was read from (Claude Code: `${CLAUDE_SKILL_DIR}`).

- **Claude Code:** run it with `run_in_background: true` and return to the user's task
  immediately. When the notification arrives, relay the last line.
- **Cursor / Codex (no background notification):** append `&> "$BRIEF.log" &` and tell the
  user the log path; the issue URL is the log's last line.

The script exits non-zero and prints the reason when no agent CLI (`claude` / `codex`) or `gh` is installed or `gh`
is not logged in. Relay that reason in one line; do not try to fix the environment.

## Step 3: Report back — one line

```
이슈 올림: https://github.com/paycrux/ai-skills/issues/123 (flow · 불편)
```

or, when the new session found the same issue already open:

```
기존 이슈에 댓글 추가: https://github.com/paycrux/ai-skills/issues/98#issuecomment-…
```

Then continue the user's original task. Do not discuss the report further unless asked.

## Rules

- Never run the reporting work (reading skill sources, `gh issue` calls) in the current session.
- One complaint = one brief = one run. Several complaints at once → one run each.
- The user asking to report is the authorization to post; do not ask for confirmation of
  the draft. The issue can be edited or closed on GitHub afterwards.
