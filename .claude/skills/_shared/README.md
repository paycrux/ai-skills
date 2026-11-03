# `_shared/` — not a skill

This directory holds code that more than one skill uses. It has no `SKILL.md`, so skill discovery
(which looks for `SKILL.md`) ignores it. The leading underscore is there to make that obvious at a
glance.

## Why it exists

`fetch_notion_markdown.py` used to live in two places — `create-prd/scripts/` and
`notion-do/scripts/` — as byte-identical copies. Nothing detected drift between them, so a fix
applied to one would silently miss the other. Since this repository has no CI, the only reliable
answer is a single copy.

It sits here rather than inside one of the two skills on purpose: skills in this repository get
removed (`git-branch`, `pr`, `test-case`, `evaluate`, `finalize`, `investigate`, `caveman`, `task-plan`, `implement`, `qa`, `tracker` so far),
and a skill that owned shared code would take its dependents down with it.

## Contents

| Path | Used by | What it does |
|---|---|---|
| `notion/fetch_notion_markdown.py` | `create-prd`, `notion-do` | Fetches a Notion page as markdown through `notion-cli` — extracts the page ID from a URL, optionally checks auth, and writes body/metadata/children to files |
| `jira/md_to_adf.py` | `flow` | Converts markdown to Atlassian Document Format for `acli ... --description-file` — the `## 기획 리뷰` description of a `[프론트]` issue `flow.py start` creates. Never emits `taskList`/`taskItem`. Moved here from `qa-guide` when that skill was removed. Also takes HTML input (legacy `tasks.html` plans) |
| `plan-format.md` | `git-pr` | Markup of the legacy `tasks.html` / `spec.html` plan documents written by the removed `task-plan` skill, and the grep recipes that read them. New work uses `/flow` task JSON |

## Referencing from a skill

Use a path relative to the calling skill's directory:

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" ...
```

This resolves for both global (`~/.claude/skills/`) and project (`./.claude/skills/`) installs,
because `install.sh` copies `skills/` recursively and `--only skills` brings this directory along.

## Adding something here

Only when a second skill actually needs it. One skill using a script is not shared code — leave it
in that skill's own `scripts/`.
