---
name: implement
description: "Document-driven implementation workflow. Repeats the cycle: per-phase approach summary → user approval → specialized agent execution → progress update."
argument-hint: "<task-folder-name or path to docs/...>"
---

# /implement — Document-Driven Implementation Workflow

Reads documents produced by task-plan (spec, tasks, findings, ui-spec) and executes implementation phase by phase.

## Argument Parsing

- `/implement <task-folder-name>` — resolves to `docs/<task-folder-name>/`
- `/implement <path>` — direct path
- `/implement` (no args) — auto-detect task with status "진행중" under `docs/`

## Step 1: Load Documents & Collect Context

### 1-1. Read Task-Plan Documents

Read **all** of the following (parallel Read):

| File | Purpose |
|---|---|
| `README.md` | Goals, scope, issue number |
| `spec.md` | Feature flows, state definitions, edge cases |
| `tasks.md` | Per-phase implementation checklist |
| `findings.md` | Related files, existing patterns, libraries, technical decisions |
| `ui-spec.md` | (if exists) Screen structure, component breakdown, reuse map |
| `progress.md` | Previous progress state |

If any required file is missing, notify the user and suggest running `/task-plan`.

### 1-2. Collect Project Context

Collect in the same way as the evaluate skill:

- `CLAUDE.md`, `.claude/rules/*.md` — project rules
- `package.json` — framework, state management, styling, test stack
- `tsconfig.json` — TypeScript config
- Top-level structure of `src/` or `app/` — architecture pattern

### 1-3. Check Progress State

Compare `progress.md` with `tasks.md`:

```
Checked items in tasks.md / total items → progress rate
Last completed Phase → determine next Phase to start
```

If there is interrupted work from a previous session, report to the user and confirm whether to resume.

## Step 2: Per-Phase Implementation Cycle

Repeat the following cycle for each Phase in `tasks.md`.

### 2-1. Classify Phase

Analyze the Phase's checklist items to determine the agent:

```
What are the Phase items primarily about?
├── Type definitions, API clients, utils, services, state management setup
│   → implement-engineering agent
├── Components, hooks, styling, screens, navigation
│   → implement-react agent
└── Mixed (data layer + UI)
    → implement-engineering first, then implement-react
```

### 2-2. Output Approach Summary

Before writing code, **briefly** summarize the implementation approach for the Phase and present it to the user.

```markdown
## Phase N: {Phase title}

### 구현 접근법
- **에이전트**: {implement-engineering / implement-react / 순차 실행}
- **대상 파일**: {files to create/modify}
- **핵심 전략**:
  - {follow existing pattern X from findings.md}
  - {reuse existing component Y for Z}
  - {apply pattern B from library A}

진행할까요?
```

**Approach summary principles:**
- Describe only the "How" for each "What" in tasks.md
- Must reflect existing patterns/library info from findings.md
- Explicitly mention if a new pattern or library is needed
- Keep it concise: 3-5 lines

### 2-3. Execute Agent

Once the user approves, launch the appropriate agent.

**Agent prompt must include:**

1. **Project context** (collected in Step 1-2)
2. **Task-plan document paths** (so the agent can read them directly)
3. **Current Phase's checklist items** (extracted from tasks.md)
4. **Related findings** (relevant portions from findings.md)
5. **Approach summary** (user-approved content from Step 2-2)
6. **ui-spec info** (if available, component/screen info for the Phase)

**For mixed Phases:**
1. Run implement-engineering first (data/logic layer)
2. After completion, run implement-react (UI layer, building on engineering output)

### 2-4. Phase Completion

After agent execution completes:

1. Check off completed items in `tasks.md` (`- [ ]` → `- [x]`)
2. Add Phase record to `progress.md`:
   ```markdown
   ### Phase N: {title} — {date}
   - 작업 내용: {summary}
   - 수정 파일: {list}
   - 현재 상태: Phase N 완료, 다음 Phase N+1
   ```
3. If technical facts were discovered during implementation, add to `findings.md`

## Step 3: Full Completion

When all Phases are done:

1. Verify all items in `tasks.md` are checked
2. Write final record in `progress.md`
3. **Auto-run `/evaluate` skill** — pass the task folder path
4. If fixes are needed based on evaluate results, run the appropriate agent
5. Change `README.md` status to "완료"
6. **QA 검증 안내** — 웹 앱 프로젝트인 경우 (ui-spec.md가 있거나, 프론트엔드 변경이 포함된 경우) 다음을 안내:

```
구현이 완료되었습니다.

브라우저 기반 QA 검증을 권장합니다.
컨텍스트가 무거워졌으므로, **새 대화에서 `/qa <task-folder-name>`을 실행**해주세요.

/qa는 task-plan 문서를 기반으로 헤드리스 브라우저로 실제 앱을 탐색하고,
버그를 발견하면 리포트를 작성한 뒤 바로 수정 여부를 확인합니다.
```

## Step 4 (Optional): Partial Execution

When the user wants to run specific Phases only:

- `/implement <task-name> phase 2` — run Phase 2 only
- `/implement <task-name> phase 2-4` — run Phases 2 through 4

## Step 5: Evaluation-Based Fixes (evaluate.md Integration)

When `evaluate.md` already exists in the task folder and the user requests fixes based on evaluation items:

### 5-1. Read evaluate.md

Read `docs/<task-name>/evaluate.md` to identify the violation list.

### 5-2. Determine Fix Targets

Confirm which items the user specified:
- "전체 수정" → fix all in CRITICAL → MAJOR → MINOR order
- Number specification (e.g., "1, 3, 5번 수정해줘") → fix only those items
- Category specification (e.g., "CRITICAL만 수정해줘") → fix only that severity

### 5-3. Classify & Execute Agents

Assign each violation to the appropriate agent based on its category:

| Evaluate Category | Agent |
|---|---|
| React Hooks, immutability, component patterns, render performance, accessibility | `implement-react` |
| Circular dependencies, functional programming, code structure, compatibility, Iterator/Generator | `implement-engineering` |
| TypeScript, security | Decide based on file context of the violation |

**Agent prompt must include:**
1. List of violations to fix (file:line, category, description)
2. Recommended actions from evaluate.md
3. Current code of the affected files
4. Project context

### 5-4. Post-Fix Handling

1. Report changes to the user after fixes are complete
2. If the user requests re-evaluation, run `/evaluate`
3. Add evaluation-based fix record to progress.md

## Rules

- **Do not implement without documents** — task-plan documents are required
- **Approach summary requires user approval before proceeding** — do not start writing code automatically
- **Prioritize existing patterns from findings.md** — new pattern introduction requires user approval
- **Update progress.md per Phase** — enables handoff even if interrupted
- **Agents write the code** — this skill only orchestrates
- **Follow `.claude/rules/react-typescript.md` rules** — include in agent prompts
- **Evaluation-based fixes are limited to violation items** — no surrounding code refactoring or extra improvements
- Communicate with the user in Korean
