# Custom Agent Authoring Guide

## Agent File Format

Place in `agents/<agent-name>.md` within the skill directory.

```markdown
---
name: <agent-name>
description: "What this agent evaluates/produces"
model: claude-sonnet-4-6    # Optional model override
---

# <Agent Name>

## Role
One-line role definition.

## Input
What this agent receives:
- Project context block
- Target files
- Specific instructions

## Evaluation Criteria / Task Definition
Numbered list of what the agent checks or produces.

## Output Format
Structured output the agent must return.

## Rules
- Hard constraints for this agent
```

## When to Use Custom Agents

| Scenario | Use custom agent? |
|---|---|
| Skill delegates parallel evaluation tasks | Yes — one agent per domain |
| Skill needs isolated context for heavy analysis | Yes — prevents context pollution |
| Skill runs a simple sequential step | No — just do it in SKILL.md |
| Skill needs a built-in agent type (Explore, Plan) | No — use `agent:` frontmatter |

## Invoking Custom Agents

From SKILL.md, reference agents via the Agent tool:

```markdown
Launch `evaluate-react` agent with:
- subagent_type: evaluate-react
- prompt: includes project context + target files
```

Or reference the file directly:
```markdown
Launch agent defined in `${CLAUDE_SKILL_DIR}/agents/grader.md`
```

## Best Practices

- **One responsibility per agent** — don't combine unrelated evaluations
- **Include project context in every agent prompt** — agents don't share parent context
- **Define output format strictly** — the parent skill needs to parse/consolidate results
- **Keep agent files under 200 lines** — they're fully loaded when invoked
