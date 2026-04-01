---
name: evaluate
description: "Run 5 evaluate agents (react, engineering, a11y, security, performance) in parallel for comprehensive code quality assessment. Use when code review is needed after implementation, or when the user requests /evaluate."
argument-hint: "[file-or-directory or task-folder-name]"
allowed-tools: ["Agent", "Read", "Glob", "Grep", "Bash", "Write", "Edit"]
effort: "high"
---

# /evaluate — Comprehensive Code Quality Assessment

Run **5 evaluate agents in parallel** to assess code quality across all dimensions: React/RN framework, engineering, accessibility, security, and performance.

## Argument Parsing

- `/evaluate` — auto-detect recently changed files via `git diff --name-only HEAD~1`
- `/evaluate <file-or-directory>` — evaluate a specific file or directory
- `/evaluate <task-folder-name>` — evaluate based on task-plan in `docs/plans/<task-folder-name>/`

## Execution

### Step 1: Collect Project Context

Refer to `${CLAUDE_SKILL_DIR}/references/project-context-guide.md` for the full collection procedure.

Organize collected info into the format defined in `${CLAUDE_SKILL_DIR}/templates/project-context-block.md`.

### Step 2: Determine Evaluation Targets

1. If argument provided → set that path as the target
2. If no argument → get changed file list via `git diff --name-only HEAD~1`
3. If a task-plan folder name is given → check `docs/plans/<folder>/progress.md` for changed files

### Step 3: Run Agents in Parallel

**Must run all 5 agents simultaneously (five Agent tool calls in a single message).**

Refer to each agent's execution guide for prompt construction:
- `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-react.md`
- `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-engineering.md`
- `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-a11y.md`
- `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-security.md`
- `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-performance.md`

Each agent prompt must include:
1. **Project context block** (Step 1)
2. **Target file list** (Step 2)
3. **Task-plan path** (if available)

### Step 4: Consolidate Results

Receive results from both agents and compose a consolidated report.
Use the template at `${CLAUDE_SKILL_DIR}/templates/report.md`.

### Step 5: Save Evaluation Report

Follow the save policy at `${CLAUDE_SKILL_DIR}/templates/save-policy.md`.

### Step 6: User Review & Fix Suggestions

Present the report to the user, then **wait for user judgment — do not auto-fix.**

Use the prompt template at `${CLAUDE_SKILL_DIR}/templates/review-prompt.md`.

#### Handling Based on User Response

| User Choice | Action |
|---|---|
| Fix all | Fix in CRITICAL → MAJOR → MINOR order, then re-run `/evaluate` |
| Selective fix | Fix only specified items, then re-run `/evaluate` |
| Keep as-is | End without fixes. If linked to task-plan, proceed to completion |

#### Fix Principles

- Fix CRITICAL first — MINOR only when explicitly requested
- Fix scope is **limited to violation items** — no surrounding code refactoring
- Re-evaluation after fixes is **max 2 times** — if violations remain, defer to user judgment

## Task-plan 연동

평가 완료 후, 관련 task-plan 폴더(`docs/plans/*/`)가 존재하면 `progress.md`에 결과 요약을 append한다:

```markdown
### /evaluate 결과 — {YYYY-MM-DD}
- 종합 등급: {A/B/C/D/F}
- CRITICAL: {N}건, MAJOR: {N}건, MINOR: {N}건
- 리포트: `{evaluate report 저장 경로}`
```

## Rules

- All 5 agents must run **in parallel** — sequential execution prohibited
- Overall grade follows the **lowest grade** among all domains
- Do not arbitrarily omit or summarize agent results — include in full
- **Must confirm with user about fixes after evaluation** — no auto-fixing
- Write output in Korean
