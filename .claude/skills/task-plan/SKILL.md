---
name: task-plan
description: "Create task folder with documentation (README, spec, findings, tasks, progress, ui-spec) for new features or bug fixes. Use when user requests /task-plan or needs structured planning before implementation."
argument-hint: <task description or Jira issue number>
allowed-tools: Read, Grep, Glob, Write, Edit
---

# /task-plan — Task Planning & Documentation Workflow

Create a structured task folder with documentation, then implement phase by phase.

## Argument Parsing

- `/task-plan <description>` — start planning with the given task description
- `/task-plan <JIRA-123>` — start planning for the given Jira issue
- `/task-plan` — ask the user what they want to build

## Execution

### Step 1: Create Task Folder

Create `docs/{task-name}/plans/` (kebab-case, no issue number in folder name).

### Step 2: Determine Task Type

```
Is this a bug fix / debugging task?
├── YES → "bug" (include investigate workflow in Step 3)
└── NO → feature / refactor
     └── Does the task involve UI/frontend work?
         ├── YES → "frontend" (include ui-spec.md, state location in spec.md)
         │   ├── UI only
         │   ├── UI + business logic
         │   └── Full-stack
         └── NO → "backend-only" (skip UI sections)
```

**Bug 판별 기준:** 사용자 설명에 에러 메시지, 비정상 동작, "안 됨", "깨짐", "crash", 버그 번호 등이 포함된 경우.

### Step 3: Explore Codebase (& Investigate if Bug)

Follow the exploration strategy in `${CLAUDE_SKILL_DIR}/references/exploration-strategy.md`.

**Bug 타입인 경우 — investigate 워크플로우 추가:**

탐색과 함께 근본 원인 분석을 수행한다.

1. **증상 수집**: 에러 메시지, 재현 조건, 기대 vs 실제 동작, `git log --oneline -10`으로 최근 변경 확인
2. **가설 생성**: 확률순으로 2-4개 가설 작성 (원인 한줄 / 근거 / 검증 방법 / 확률)
3. **사용자 확인**: "다음 가설 중 어떤 것부터 검증할까요?" — 사용자 선택 대기
4. **검증 루프**: 선택된 가설에 대해 코드 추적 → 확인/기각 (최대 3회)
5. **근본 원인 기록**: 확인된 원인을 findings.md의 별도 섹션에 기록

```markdown
<!-- findings.md에 추가되는 섹션 (bug 타입만) -->

## 근본 원인 분석

### 증상
| 항목 | 내용 |
|------|------|
| 증상 | {에러 메시지 또는 비정상 동작} |
| 재현 조건 | {재현 단계} |
| 기대 동작 | {정상 동작} |
| 실제 동작 | {현재 동작} |

### 검증된 가설
| # | 가설 | 결과 | 비고 |
|---|------|------|------|
| 1 | {가설} | 확인/기각 | {이유} |

### 근본 원인
**원인**: {한 줄 요약}
**발생 경로**: {코드 실행 흐름}
**관련 코드**: {file:line}

### 수정 방안
**권장 수정**: {최소한의 수정 방법}
**영향 범위**: {수정 시 영향받는 파일/기능}
```

Record all results in `findings.md`.

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

#### White Label Pattern Reference (applied when writing `ui-spec.md`)

If the project is `white_label` and the task involves `apps/partner/` or `apps/admin/`, inspect the Figma link or design requirements before writing `ui-spec.md`:

| Detected UI pattern | Action |
|---|---|
| Table / data grid | Read `.claude/docs/partner-jirisan.md` → confirm with user → embed pattern constraints in `ui-spec.md` component breakdown |
| Search bar / filter panel | Read `.claude/docs/partner-option-group-factory.md` → confirm with user → embed pattern constraints in `ui-spec.md` component breakdown |

Embed the relevant pattern as a `## Pattern Reference` section inside `ui-spec.md` so implement and evaluate can use it without re-reading the source doc.

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
2. Self-evaluate document quality against the compliance checklist:
   - All required files exist (README, spec, tasks, findings, progress; ui-spec if frontend)
   - spec.md flows are concrete (no vague "appropriately", "if needed")
   - tasks.md covers all spec.md flows
   - Cross-document consistency (README scope ↔ spec flows ↔ tasks items)
   - Fix any gaps found before proceeding

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

## PRD Change → Task-plan Update

When the user says the PRD has changed and asks to update the task-plan:

1. **Never modify already-completed items** — tasks marked done (`- [x]`) in `tasks.md` or logged as done in `progress.md` must not be altered
2. Add new requirements as a **new phase** appended to the bottom of `tasks.md` (e.g., Phase N+1)
3. Update supporting documents by **appending only** — never rewrite or restructure existing sections:
   - **README.md** — append updated scope/requirements (overview only, no implementation detail)
   - **tasks.md** — add the new phase with concrete implementation steps
   - **progress.md** — record that the PRD changed, what was added, and when
   - **spec.md / ui-spec.md** — add new sections for the added scope
   - **findings.md** — note architectural or technical implications of the new requirements

## Rules

- Write all documents at once, not one at a time
- Never skip the compliance check before evaluation
- Always use `${CLAUDE_SKILL_DIR}` for file references, not relative paths
- Output in the same language the user is using
