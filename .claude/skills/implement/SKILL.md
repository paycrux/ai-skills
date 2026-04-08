---
name: implement
description: "Document-driven implementation workflow. Repeats the cycle: per-phase approach summary → user approval → direct implementation → progress update."
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

### 1-2. Check Progress State

Compare `progress.md` with `tasks.md`:

```
Checked items in tasks.md / total items → progress rate
Last completed Phase → determine next Phase to start
```

If there is interrupted work from a previous session, report to the user and confirm whether to resume.

## Step 2: Per-Phase Implementation Cycle

Repeat the following cycle for each Phase in `tasks.md`.

### 2-1. Output Approach Summary

Before writing code, **briefly** summarize the implementation approach for the Phase and present it to the user.

```markdown
## Phase N: {Phase 제목}

### 구현 접근법
- **대상 파일**: {생성/수정할 파일}
- **핵심 전략**:
  - {findings.md의 기존 패턴 X를 따름}
  - {기존 컴포넌트 Y를 Z에 재사용}
  - {라이브러리 A의 패턴 B를 적용}

진행할까요?
```

**접근법 요약 원칙:**
- tasks.md의 각 "무엇"에 대한 "어떻게"만 기술
- findings.md의 기존 패턴/라이브러리 정보를 반드시 반영
- 새로운 패턴이나 라이브러리 도입 시 명시
- 간결하게: 3-5줄

### 2-2. Implement Directly

Once the user approves, implement the Phase directly. Follow:
- `.claude/rules/react-typescript.md` for frontend code
- Existing patterns identified in `findings.md`
- Component reuse map from `ui-spec.md` (if available)

### 2-3. Phase Completion

After implementation completes:

1. Check off completed items in `tasks.md` (`- [ ]` → `- [x]`)
2. Add Phase record to `progress.md`:
   ```markdown
   ### Phase N: {제목} — {날짜}
   - 작업 내용: {요약}
   - 수정 파일: {목록}
   - 현재 상태: Phase N 완료, 다음 Phase N+1
   ```
3. If technical facts were discovered during implementation, add to `findings.md`

## Step 3: Full Completion

When all Phases are done:

1. Verify all items in `tasks.md` are checked
2. Write final record in `progress.md`
3. Change `README.md` status to "완료"
4. Suggest running `/evaluate` if the user wants a code quality review
5. **QA guidance** — for web app projects (ui-spec.md exists or frontend changes included):

```
구현이 완료되었습니다.

브라우저 기반 QA 검증을 권장합니다.
컨텍스트가 무거우므로, **새 대화에서 `/qa <task-folder-name>`을 실행해주세요**.

/qa는 task-plan 문서를 기반으로 헤드리스 브라우저로 실제 앱을 탐색하고,
발견된 버그를 스크린샷과 함께 리포트합니다.
```

## Step 4 (Optional): Partial Execution

When the user wants to run specific Phases only:

- `/implement <task-name> phase 2` — run Phase 2 only
- `/implement <task-name> phase 2-4` — run Phases 2 through 4

## Step 5: Evaluation-Based Fixes

When `evaluate.md` already exists in the task folder and the user requests fixes:

### 5-1. Read evaluate.md

Read `docs/<task-name>/evaluate.md` to identify the violation list.

### 5-2. Determine Fix Targets

Confirm which items the user specified:
- "전체 수정" → fix all in CRITICAL → MAJOR → MINOR order
- Number specification (e.g., "1, 3, 5번 수정해줘") → fix only those items
- Category specification (e.g., "CRITICAL만 수정해줘") → fix only that severity

### 5-3. Fix Directly

Fix violations directly in the main conversation. Fix scope is **limited to violation items** — no surrounding code refactoring.

### 5-4. Post-Fix Handling

1. Report changes to the user after fixes are complete
2. If the user requests re-evaluation, run `/evaluate`
3. Add evaluation-based fix record to progress.md

## Rules

- **Do not implement without documents** — task-plan documents are required
- **Approach summary requires user approval before proceeding** — do not start writing code automatically
- **Prioritize existing patterns from findings.md** — new pattern introduction requires user approval
- **Update progress.md per Phase** — enables handoff even if interrupted
- **Follow `.claude/rules/react-typescript.md` rules** for frontend code
- **Evaluation-based fixes are limited to violation items** — no surrounding code refactoring or extra improvements
- 산출물과 사용자 소통은 한국어로
