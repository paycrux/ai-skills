---
name: task-plan
description: "Create task folder with documentation (README, spec, findings, tasks, progress, ui-spec) for new features or bug fixes. Use when user requests /task-plan or needs structured planning before implementation."
argument-hint: <task description or Jira issue number>
allowed-tools: Read, Grep, Glob, Agent, Write, Edit
---

# /task-plan — Task Planning & Documentation Workflow

Create a structured task folder with documentation, then implement phase by phase.

## Argument Parsing

- `/task-plan <description>` — start planning with the given task description
- `/task-plan <JIRA-123>` — start planning for the given Jira issue
- `/task-plan` — ask the user what they want to build

## Execution

### Step 1: Create Task Folder

Create `docs/plans/{task-name}/` (kebab-case, no issue number in folder name).

### Step 2: Determine Task Type

```
Does the task involve UI/frontend work?
├── YES → "frontend" (include ui-spec.md, state location in spec.md)
│   ├── UI only
│   ├── UI + business logic
│   └── Full-stack
└── NO → "backend-only" (skip UI sections)
```

### Step 3: Explore Codebase

Use the Explore sub-agent following `${CLAUDE_SKILL_DIR}/references/exploration-strategy.md`.

Record results in `findings.md`.

### Step 4: Analyze Reference Documents

If the user attaches design docs, API specs, or implementation guides:

| Source content | Distribute to |
|---|---|
| Background/purpose | README.md → 배경, 목표 |
| Feature flows | spec.md → 화면/기능 흐름 |
| API endpoints | spec.md → API 연동 |
| State/edge cases | spec.md → 상태 정의, 엣지 케이스 |
| Implementation methods | tasks.md → Phase checklists |
| Existing code/deps | findings.md → 직접 관련 |
| Technical decisions | findings.md → 기술 결정 |

**Principle:** distribute reference content across plan files so originals are not needed later.

For Figma/design handling, refer to `${CLAUDE_SKILL_DIR}/references/design-handling.md`.

### Step 5: Write Documents

Write **all documents at once** in this order using templates from `${CLAUDE_SKILL_DIR}/templates/`:

1. `README.md` — overview, issue number, goals, scope
2. `spec.md` — pseudocode, behavior flows, state definitions (+ state location if frontend)
3. `ui-spec.md` — **(frontend only)** screen structure, components, state×display matrix
4. `findings.md` — exploration results (+ component reuse map if frontend)
5. `tasks.md` — implementation checklist based on spec + findings
6. `progress.md` — initialize (empty)

> `spec.md`의 "상태 위치 결정"이 `ui-spec.md`의 컴포넌트 분해를 결정한다. spec.md를 먼저 쓸 것.

### Step 6: Validate & Evaluate

1. Run compliance check per `${CLAUDE_SKILL_DIR}/references/compliance-checklist.md`. Fix failures before proceeding.
2. Run `evaluate-docs` agent per `${CLAUDE_PROJECT_DIR}/.claude/agents/evaluate-docs.md` (pass task folder path).
   - Grade B+ → proceed to Step 7
   - Grade C or below → fix CRITICAL/MAJOR items, re-evaluate (max 2 times)
   - Still C after 2 retries → proceed as-is, share results

### Step 7: User Review

- "문서 작성을 완료했습니다. 검토 후 수정할 내용이 있으면 알려주세요."
- Apply requested changes, record in `progress.md`.

## Phase 1–N: Implementation

Start after user approval. Follow `tasks.md` checklist in order.

**After each phase:**
- Record in `progress.md`: work done, modified files, current status
- Update `tasks.md` checklist (`- [ ]` → `- [x]`)
- Add technical discoveries to `findings.md`

**Frontend tasks:** read `.claude/rules/react-typescript.md` before starting.

### When Direction Changes

1. Record in `progress.md` (before → after → reason)
2. Update `spec.md` and `tasks.md`
3. Do not update `README.md` unless the goal itself changed

## Task Completion

1. Verify all `tasks.md` items checked
2. Write final session entry in `progress.md`
3. Auto-run `/evaluate` with task folder path
4. Change `README.md` status to "완료"

## Session Handoff

1. Read `progress.md` for last state
2. Check `tasks.md` for remaining work
3. Restore context from `findings.md`
4. Report status to user, then continue

## Creating a PR

- Reference all plan files (5~6 files)
- Issue number in PR title
- PR body: overview (README) / changes (tasks + changed files) / review focus (findings decisions)

## Rules

- Write all documents at once, not one at a time
- Never skip the compliance check before evaluation
- Always use `${CLAUDE_SKILL_DIR}` for file references, not relative paths
- Output in the same language the user is using
