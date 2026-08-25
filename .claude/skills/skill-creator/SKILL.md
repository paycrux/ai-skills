---
name: skill-creator
description: "Scaffold and author Claude Code skills with proper structure, frontmatter, and best practices. Use when creating a new skill, refactoring an existing skill, or reviewing skill quality."
argument-hint: "[skill-name or existing-skill-path]"
---

# /skill-creator — Claude Code Skill Authoring Assistant

Create, refactor, or review Claude Code skills following official best practices.

## Argument Parsing

- `/skill-creator <new-skill-name>` — scaffold a new skill from scratch
- `/skill-creator <existing-skill-path>` — refactor/review an existing skill
- `/skill-creator` — interactive mode: ask what the user wants to build

## Execution

### Step 1: Understand the Skill's Purpose

Ask the user (skip if already clear from context):

1. **What does this skill do?** — core action in one sentence
2. **When should it trigger?** — specific trigger patterns (slash command only? auto-trigger?)
3. **What tools/agents does it need?** — bash scripts, subagents, external tools
4. **What does it output?** — files, console output, both

### Step 2: Determine Directory Structure

Based on the skill's complexity, select which directories are needed.
Refer to `${CLAUDE_SKILL_DIR}/references/directory-structure.md` for the full directory spec.

```
<skill-name>/
├── SKILL.md              # Always required
├── references/           # If skill needs deep docs (>500 lines total)
├── templates/            # If skill produces structured output
├── agents/               # If skill delegates to custom subagents
├── scripts/              # If skill runs automated commands
└── assets/               # If skill uses static resources
```

**Minimal skill** (simple action): Only `SKILL.md`
**Medium skill** (structured output): `SKILL.md` + `templates/`
**Complex skill** (multi-agent, multi-step): Full structure

### Step 3: Write Frontmatter

Compose the SKILL.md frontmatter. Refer to `${CLAUDE_SKILL_DIR}/references/frontmatter-spec.md` for all available fields and guidelines.

Required decisions:
- `name`: lowercase, hyphens, max 64 chars
- `description`: max 250 chars effective (truncated in listing). Front-load key use case + trigger conditions
- `argument-hint`: show expected input format
- `disable-model-invocation`: set `true` for side-effectful skills (deploy, send, commit)
- `user-invocable`: set `false` for passive knowledge skills

### Step 4: Write SKILL.md Body

Follow these principles:

1. **Keep under 500 lines** — move deep detail to `references/`
2. **Execution steps numbered** — Step 1, Step 2, ... with clear purpose per step
3. **Decision trees explicit** — use tables or flowcharts, not prose
4. **Output format in templates/** — not inline in SKILL.md
5. **Policies in templates/** — save strategies, naming rules, etc.
6. **Reference docs in references/** — context that's only needed sometimes

Refer to `${CLAUDE_SKILL_DIR}/references/writing-guide.md` for SKILL.md body authoring rules.

### Step 5: Create Supporting Files

For each directory decided in Step 2:

#### references/
- Each file ≤ 200 lines; add TOC if > 100 lines
- One level deep only (no nested references)
- Claude loads these on-demand — large docs are free until needed

#### templates/
- Output format templates with `{placeholder}` markers
- Policy/strategy docs for file operations
- Each template is a standalone file

#### agents/
- One `.md` file per custom subagent
- Define the agent's role, evaluation criteria, and output format
- Refer to `${CLAUDE_SKILL_DIR}/references/agent-authoring.md`

#### scripts/
- Executable scripts Claude runs via bash
- Use `${CLAUDE_SKILL_DIR}/scripts/<name>` for stable paths
- Only output consumes tokens, not script source

### Step 6: Validate

Run through this checklist:

| Check | Pass criteria |
|---|---|
| SKILL.md < 500 lines | Line count check |
| Description < 250 chars effective | Front-loaded, includes triggers |
| No inline templates | All output formats in `templates/` |
| No inline policies | All strategies/rules in `templates/` or `references/` |
| References ≤ 200 lines each | With TOC if > 100 |
| References one level deep | No SKILL → ref → ref chains |
| Frontmatter complete | All relevant fields set |
| `${CLAUDE_SKILL_DIR}` used for paths | Not relative paths |

Present validation results and fix any issues.

### Step 7: Placement

| Scope | Path |
|---|---|
| Personal (all projects) | `~/.claude/skills/<skill-name>/` |
| Project-specific | `.claude/skills/<skill-name>/` |

Ask the user where to place the skill, then write all files.

## Communication Style

Write for a reader who has not implemented this feature and does not share your context.

- Explain the background before the conclusion. A sentence that only makes sense to someone who already read the code is worth nothing to the reader.
- Never drop an internal term without unpacking it. Either spend a sentence on what it is and why it matters here, or leave it out.
- When the background costs more than two or three sentences to explain, compress the whole point to one line instead.
- No filler: 전반적으로, ~등을 개선, 안정성 향상 and the like add length without information.

This applies to conversational output in this flow (Step 1 questions, Step 6 validation results, Step 7 placement prompt), not to the scaffolded skill's own SKILL.md/references/templates content — those follow the target skill's own conventions.

## Rules

- Never create a skill with only SKILL.md if it has structured output — always use `templates/`
- Always use `${CLAUDE_SKILL_DIR}` for referencing bundled files
- Description must include both **what it does** AND **when to trigger**
- Side-effectful skills must set `disable-model-invocation: true`
- 산출물은 한국어로 작성
