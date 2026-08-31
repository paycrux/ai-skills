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
removed (`git-branch`, `pr`, `test-case`, `evaluate`, `finalize`, `investigate`, `caveman` so far),
and a skill that owned shared code would take its dependents down with it.

## Contents

| Path | Used by | What it does |
|---|---|---|
| `notion/fetch_notion_markdown.py` | `create-prd`, `notion-do` | Fetches a Notion page as markdown through `notion-cli` — extracts the page ID from a URL, optionally checks auth, and writes body/metadata/children to files |

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
