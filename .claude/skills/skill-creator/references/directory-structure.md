# Skill Directory Structure Reference

## Full Structure

```
<skill-name>/
├── SKILL.md              # Required — entrypoint with frontmatter + execution flow
├── references/           # Deep docs loaded progressively (on-demand)
│   ├── <topic>.md        # Each ≤ 200 lines, TOC if > 100 lines
│   └── ...
├── templates/            # Output formats, policies, strategies
│   ├── <output>.md       # Structured output with {placeholder} markers
│   └── <policy>.md       # Save/write/naming rules
├── agents/               # Custom subagent definitions
│   ├── <agent-name>.md   # Role, criteria, output format per agent
│   └── ...
├── scripts/              # Executable automation (bash, python, etc.)
│   ├── <script>.sh       # Claude runs via bash, only output consumes tokens
│   └── ...
└── assets/               # Static resources (HTML viewers, icons, etc.)
    └── ...
```

## When to Use Each Directory

| Directory | Use when... | Token cost |
|---|---|---|
| `references/` | Skill needs deep context docs (API specs, rule details, guides) | Zero until read |
| `templates/` | Skill produces structured output or has file operation policies | Zero until read |
| `agents/` | Skill delegates work to custom subagents | Zero until read |
| `scripts/` | Skill runs automated commands (git, file collection, validation) | Output only |
| `assets/` | Skill uses static files (HTML templates, viewers) | Zero until read |

## Complexity Tiers

### Minimal (SKILL.md only)
- Simple actions: lint check, format, quick lookup
- No structured output
- No subagent delegation

### Medium (SKILL.md + templates/)
- Produces reports, documents, or structured files
- Has file save policies
- Example: `/qa-guide`, `/study`

### Full (all directories)
- Multi-step workflow with parallel agents
- Deep reference material needed conditionally
- Automated scripts for data collection
- Example: `/evaluate`, `/task-plan`

## Progressive Loading Behavior

1. **Startup**: Only `name` + `description` from frontmatter loaded (250 char effective limit)
2. **Trigger**: Full SKILL.md body loaded
3. **On-demand**: `references/`, `templates/`, `agents/` read only when Claude navigates to them
4. **Scripts**: Executed via bash — source code never enters context, only output

This means large reference docs are free until needed. Bundle generously.
