# Investigation Save Policy

## Output Path

| Condition | Output path |
|---|---|
| Task-plan exists for this issue | `docs/plans/<task-name>/findings.md` (merge with existing) |
| No task-plan, project has `docs/` | `docs/investigate/<slug>.md` |
| No task-plan, no `docs/` | `.claude/investigate/<slug>.md` |

## File Naming

`<slug>` = kebab-case summary of the issue (e.g., `login-token-expired`, `order-list-crash`)

## Write Strategy

```
Does findings file already exist at the target path?
├── YES → Append new investigation
│   - Add a horizontal rule (---) separator
│   - Add timestamp header: `## 재조사 — {YYYY-MM-DD HH:mm}`
│   - Append the full findings below
└── NO → Create new file with the full findings template
```

## Rules

- Always print the saved file path so the user knows where findings were written
- If a task-plan's `findings.md` already exists, append — don't overwrite
- Keep each investigation as a self-contained section (readable standalone)
