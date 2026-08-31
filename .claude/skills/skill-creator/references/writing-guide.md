# SKILL.md Body Writing Guide

## Structure Pattern

```markdown
# /<skill-name> — One-line Purpose

Brief overview (1-2 sentences).

## Argument Parsing
- How arguments are interpreted

## Execution
### Step 1: ...
### Step 2: ...
### Step N: ...

## Output Format
Reference to templates/

## Rules
- Hard constraints
```

## Principles

### 1. Split by When It's Needed, Not by What It Is
`SKILL.md` is fully loaded when triggered, so the only real saving is moving out what a given run
does **not** need.

- Always consulted (authoring rules the skill applies every time) → keep inline. Moving it to
  `references/` costs a read and saves nothing.
- Only some branches need it (a lookup for one flag, a format used by one mode) → `references/`.
- Output formats → `templates/`, always.
- Still over 500 lines with only always-needed content left? The skill is doing two jobs. Split the
  skill, not the file.

### 2. Steps Are Actions, Not Descriptions
Each step should be an imperative action Claude can execute.

Good: `### Step 2: Run Agents in Parallel`
Bad: `### Step 2: About the Agents`

### 3. Decision Trees Are Explicit
Use tables or flowcharts, never ambiguous prose.

Good:
```
| Condition | Action |
|---|---|
| File exists | Append |
| File missing | Create |
```

Bad:
"If the file exists you might want to append, otherwise create it."

### 4. Reference External Files with ${CLAUDE_SKILL_DIR}
```markdown
Refer to `${CLAUDE_SKILL_DIR}/references/api-spec.md` for details.
```
Not: "See references/api-spec.md"

### 5. Separate Concerns

| Content type | Location |
|---|---|
| Execution flow (steps) | SKILL.md |
| Rules applied on every run | SKILL.md |
| Output format (templates) | `templates/<name>.md` |
| Lookups/policies only some branches need | `references/<topic>.md` |
| Deep reference docs | `references/<topic>.md` |
| Agent prompts | `agents/<name>.md` |
| Automation scripts | `scripts/<name>.sh` |

### 6. Rules Section at Bottom
- Hard constraints that apply across all steps
- Keep it a flat bullet list
- Each rule is one line, actionable

## Anti-Patterns to Avoid

- **Wall of text**: Long prose paragraphs instead of structured steps
- **Inline everything**: Templates and branch-specific lookups sitting in SKILL.md
- **Extract everything**: Splitting out rules the skill needs on every run — pure overhead, no saving
- **Vague triggers**: Description that doesn't tell Claude when to activate
- **Missing argument parsing**: No guidance on how to interpret user input
- **Nested references**: SKILL.md → ref A → ref B (keep one level deep)
- **Over-engineering**: Adding directories the skill doesn't need
