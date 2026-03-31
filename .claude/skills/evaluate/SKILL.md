---
name: evaluate
description: "Run evaluate-react and evaluate-engineering agents in parallel for comprehensive code quality assessment."
argument-hint: "[file-or-directory or task-folder-name]"
---

# /evaluate — Comprehensive Code Quality Assessment

Run `evaluate-react` and `evaluate-engineering` agents **in parallel** to assess React/RN framework-level and TypeScript/JS engineering-level quality simultaneously.

## Argument Parsing

- `/evaluate` — auto-detect recently changed files via `git diff --name-only HEAD~1`
- `/evaluate <file-or-directory>` — evaluate a specific file or directory
- `/evaluate <task-folder-name>` — evaluate based on task-plan in `docs/plans/<task-folder-name>/`

## Execution

### Step 1: Collect Project Context

Collect project context to pass to agents. Search the following sources **in order**, collecting only what exists.

#### 1-1. Project Rules
- `CLAUDE.md` (project root) — project-wide rules, conventions
- `.claude/rules/*.md` — detailed rule files
- `.cursorrules`, `.cursor/rules/*.md` — Cursor rules (if present)
- `eslint.config.*`, `.eslintrc.*` — lint rules
- `tsconfig.json` — TypeScript settings (strict mode, paths, etc.)
- `.prettierrc*` — formatting rules

#### 1-2. Project Structure & Dependencies
- `package.json` — dependencies, devDependencies, scripts (identify framework and library stack)
- Key dependencies to identify from `package.json`:
  - Framework: React vs React Native vs Next.js, etc.
  - State management library (Redux, Zustand, Recoil, Jotai, etc.)
  - Styling approach (styled-components, Tailwind, CSS Modules, etc.)
  - Test framework (Jest, Vitest, Testing Library, etc.)

#### 1-3. Directory Structure (top 1-2 levels)
- `ls src/` or `ls app/` to identify architecture pattern
  - feature-based, layer-based, or hybrid

Organize collected context into a **project context block** and include identically in both agent prompts.

```
## Project Context
- Framework: {React Native 0.76 / Next.js 15 / etc.}
- State management: {Redux Toolkit + Redux-Saga / Zustand / etc.}
- Styling: {styled-components / Tailwind / etc.}
- TypeScript: {strict: true/false, paths config}
- Key rules: {summary of evaluation-relevant items from CLAUDE.md or rules}
- Directory structure: {one-line architecture pattern summary}
```

### Step 2: Determine Evaluation Targets

1. If argument provided, set that path as the target
2. If no argument, get changed file list via `git diff --name-only HEAD~1`
3. If a task-plan folder name is given, check `docs/plans/<folder>/progress.md` for changed files

### Step 3: Run Agents in Parallel

**Must run both agents simultaneously (two Agent tool calls in a single message).**

Each agent prompt must include all three of the following:
1. **Project context block** (collected in Step 1)
2. **Target file list** (determined in Step 2)
3. **Task-plan path** (if available)

#### evaluate-react Agent
- React/RN framework-level evaluation: hooks, immutability, component patterns, performance, security
- Reflect project-specific patterns (state management library, styling approach, etc.) through project context

#### evaluate-engineering Agent
- Engineering-level evaluation: circular dependencies, functional programming, code structure, compatibility
- Reflect TypeScript settings, module structure, existing patterns through project context

### Step 4: Consolidate Results

Receive results from both agents and compose a consolidated report in the following format.

## Output Format

```markdown
# 코드 품질 종합 평가

## 평가 대상
- 파일: {file list}
- 관련 태스크: {task-plan reference or "없음"}

## 종합 등급

| 영역 | 등급 | CRITICAL | MAJOR | MINOR |
|------|------|----------|-------|-------|
| React/RN | {grade} | {count} | {count} | {count} |
| Engineering | {grade} | {count} | {count} | {count} |
| **종합** | **{grade}** | **{count}** | **{count}** | **{count}** |

> 종합 등급은 두 영역 중 낮은 등급을 따른다.

---

## React/RN 평가 결과

{full evaluate-react result}

---

## Engineering 평가 결과

{full evaluate-engineering result}

---

## 종합 권장 조치 (우선순위순)

1. {CRITICAL actions first}
2. {MAJOR actions}
3. {MINOR actions}
```

### Step 5: Save Evaluation Report as Markdown

After composing the report in Step 4, persist it as a markdown file.

#### Determine output path

| Condition | Output path |
|---|---|
| A specific folder path was provided as argument (e.g. `/evaluate docs/plans/my-task/`) | `<given-path>/evaluate.md` |
| A task-plan folder name was provided (e.g. `/evaluate my-task`) | `docs/plans/<my-task>/evaluate.md` |
| No path given (e.g. bare `/evaluate`) | `docs/evaluate/evaluate.md` (create `docs/evaluate/` if it does not exist) |

#### Write strategy: update existing file, do not create duplicates

```
Does evaluate.md already exist at the target path?
├── YES → append a new evaluation entry to the existing file
│   - Add a horizontal rule (---) separator
│   - Add a timestamp header: `## 재평가 — {YYYY-MM-DD HH:mm}`
│   - Append the full report from Step 4 below the header
│   - Previous evaluation entries remain intact for history
└── NO → create evaluate.md with the full report from Step 4
```

Do **not** create timestamped files like `evaluate-<date>.md`. A single `evaluate.md` file accumulates all evaluation history for one task.

#### File content

Write the full report from Step 4 into the markdown file. Do not truncate or summarize — the file must contain the complete report.

#### Rules

- When the target directory does not exist, create it before writing.
- Always use a single `evaluate.md` per target — append to it, never create separate files.
- After saving, print the file path so the user knows where the report was written.

### Step 6: User Review & Fix Suggestions

Present the evaluation report to the user, then **wait for user judgment — do not auto-fix.**

#### Report Presentation Format

After outputting the report, ask the user in this format:

```
CRITICAL/MAJOR 위반이 {N}건 발견되었습니다.

수정이 필요한 항목:
1. [CRITICAL] {file:line} — {one-line description}
2. [MAJOR] {file:line} — {one-line description}
...

다음 중 선택해주세요:
(1) 전체 수정 진행
(2) 선택적 수정 (번호 지정)
(3) 현재 상태로 유지
```

#### Handling Based on User Response

| User Choice | Action |
|---|---|
| Fix all | Fix in CRITICAL → MAJOR → MINOR order, then re-run `/evaluate` |
| Selective fix | Fix only specified items, then re-run `/evaluate` |
| Keep as-is | End without fixes. If linked to task-plan, proceed to completion |

#### Fix Principles

- Fix CRITICAL first — MINOR only when explicitly requested by the user
- Fix scope is **limited to violation items** — no surrounding code refactoring or improvements
- Re-evaluation after fixes is **max 2 times** — if violations remain after 2 re-evaluations, defer to user judgment

## Rules

- Both agents must run **in parallel** — sequential execution prohibited
- Overall grade follows the **lower grade** of the two domains
- Do not arbitrarily omit or summarize agent results — include in full
- **Must confirm with user about fixes after evaluation** — no auto-fixing
- Write output in Korean
