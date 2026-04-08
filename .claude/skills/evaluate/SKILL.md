---
name: evaluate
description: "Checklist-based code quality evaluation. Assess code across React, engineering, accessibility, security, and performance domains directly in the main conversation. No sub-agents."
argument-hint: "[file-or-directory or task-folder-name]"
---

# /evaluate — Code Quality Evaluation

Evaluate code quality across 5 domains using a checklist. Runs directly in the main conversation — no sub-agents.

## Argument Parsing

- `/evaluate` — auto-detect recently changed files via `git diff --name-only HEAD~1`
- `/evaluate <file-or-directory>` — evaluate a specific file or directory
- `/evaluate <task-folder-name>` — evaluate based on task-plan in `docs/<task-folder-name>/`

## Step 1: Determine Targets

1. If argument provided → set that path as the target
2. If no argument → get changed file list via `git diff --name-only HEAD~1`
3. If a task-plan folder name is given → check `docs/<folder>/progress.md` for changed files

Read all target files.

## Step 2: Evaluate by Checklist

Evaluate each target file against the checklist below. Each violation gets a severity:
- **CRITICAL**: causes runtime errors, infinite loops, memory leaks, or security vulnerabilities
- **MAJOR**: severely hinders maintainability, high bug probability
- **MINOR**: a better pattern exists but current code has no functional issues

### React / Accessibility

- Hooks called at top level only (no conditional/loop hooks)
- State immutability (no direct mutation, spread at all levels)
- Stable list keys (no array index for reorderable lists)
- No useEffect for derivable values or event-driven logic
- Prop drilling ≤ 2 levels (else context/composition)
- useMemo/useCallback only when measured or passing to memoized children
- ARIA attributes present on interactive elements
- Keyboard navigability (focus visible, tab order)
- Color contrast ≥ 4.5:1
- Form labels and error announcements

### Engineering / Performance

- No circular dependencies (direct or via barrel files)
- No side effects in pure functions
- No nested conditionals 3+ levels (use early return/guard)
- No nested ternary 2+ levels
- Single function ≤ 50 lines, single file ≤ 300 lines
- DRY: no 10+ similar lines repeated in 2+ places
- if-else chain 3+ on same variable → use mapper object
- No hardcoded magic numbers/strings
- Export signature changes verified against all call sites
- Unnecessary re-renders (new object/array/function created in render passed to children)
- Bundle size impact of new dependencies
- Large data loaded entirely into memory when streaming/pagination possible

### Security

- No XSS (dangerouslySetInnerHTML, unescaped user input)
- No SQL/NoSQL injection
- No hardcoded secrets/credentials
- Authentication/authorization checks on protected routes
- Input validation at system boundaries

## Step 3: Compose Report

Use the template at `${CLAUDE_SKILL_DIR}/templates/report.md`.

### Grade Criteria

| Grade | Criteria |
|---|---|
| A | No CRITICAL/MAJOR, MINOR ≤ 2 |
| B | No CRITICAL, MAJOR 1-2 |
| C | No CRITICAL, MAJOR 3+ |
| D | CRITICAL 1 |
| F | CRITICAL 2+ |

Overall grade follows the **lowest grade** among all domains.

## Step 4: Save Report

Follow the save policy at `${CLAUDE_SKILL_DIR}/templates/save-policy.md`.

## Step 5: User Review & Fix Suggestions

Present the report, then **wait for user judgment — do not auto-fix.**

Use the prompt template at `${CLAUDE_SKILL_DIR}/templates/review-prompt.md`.

### Handling Based on User Response

| User Choice | Action |
|---|---|
| Fix all | Fix in CRITICAL → MAJOR → MINOR order directly, then re-run `/evaluate` |
| Selective fix | Fix only specified items directly, then re-run `/evaluate` |
| Keep as-is | End without fixes. If linked to task-plan, proceed to completion |

### Fix Principles

- Fix CRITICAL first — MINOR only when explicitly requested
- Fix scope is **limited to violation items** — no surrounding code refactoring
- Re-evaluation after fixes is **max 2 times** — if violations remain, defer to user judgment

## Task-plan Integration

After evaluation, if a related task-plan folder (`docs/*/`) exists, append a summary to `progress.md`:

```markdown
### /evaluate result — {YYYY-MM-DD}
- Overall grade: {A/B/C/D/F}
- CRITICAL: {N}, MAJOR: {N}, MINOR: {N}
- Report: `{evaluate report path}`
```

## Rules

- **Include file path and line number for every violation**
- Overall grade follows the **lowest grade** among all domains
- **Must confirm with user about fixes after evaluation** — no auto-fixing
- If no violations found, honestly report "No violations"
- 산출물은 한국어로 작성
