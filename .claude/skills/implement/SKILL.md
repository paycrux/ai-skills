---
name: implement
description: "Document-driven implementation workflow. Repeats the cycle: per-phase approach summary → user approval → direct implementation → progress update."
argument-hint: "<task-folder-name or path to docs/...>"
---

# /implement — Document-Driven Implementation Workflow

Reads documents produced by `/task-plan` (`tasks.md`, `spec.md`) and executes implementation phase by phase.

## Argument Parsing

- `/implement <task-folder-name>` — resolves to `docs/<task-folder-name>/plans/`
- `/implement <path>` — direct path to a `plans/` directory
- `/implement` (no args) — auto-detect by grepping `docs/*/plans/tasks.md` for `상태: 진행중`

If multiple "진행중" tasks are found, list them and ask the user to pick.

## Step 1: Load Documents & Check Progress

### 1-1. Read Task-Plan Documents

Read both files in parallel:

| File | Purpose |
|---|---|
| `tasks.md` | Header (issue, type, status, date), per-phase checklist with reuse/pattern sub-bullets, `## 진행 기록` |
| `spec.md` | Feature flows, state definitions, edge cases |

If either file is missing, stop and suggest running `/task-plan`.

### 1-2. Check Progress State

From `tasks.md`:

```
Checked items / total items → progress rate
Last entry in `## 진행 기록` → determine next Phase to start
```

If there is interrupted work, report to the user and confirm whether to resume.

## Step 2: Per-Phase Implementation Cycle

Repeat for each Phase in `tasks.md`.

### 2-1. Output Approach Summary

Before writing code, briefly summarize the approach and present it to the user. Pull inputs from:

- The Phase task line in `tasks.md` — file path, optional figma node link
- Sub-bullets under the task line — `재사용:` (existing component to reuse), `패턴:` (existing library/pattern)
- `spec.md` — relevant flows / states / edge cases
- Direct codebase exploration only when sub-bullets are missing or insufficient

```markdown
## Phase N: {Phase 제목}

### 구현 접근법
- **대상 파일**: {생성/수정할 파일}
- **핵심 전략**:
  - {tasks.md sub-bullet의 재사용 컴포넌트 또는 패턴}
  - {spec.md의 엣지 케이스 반영 포인트}

진행할까요?
```

**접근법 요약 원칙:**
- tasks.md의 각 "무엇"에 대한 "어떻게"만 기술
- tasks.md sub-bullet의 재사용/패턴 정보를 반드시 반영
- 새로운 패턴이나 라이브러리 도입 시 명시
- 간결하게: 3-5줄

### 2-2. Implement Directly

Once the user approves, implement the Phase directly. Follow:

- `.claude/rules/react-typescript.md` for frontend code
- **렌더링 이슈는 구조로 먼저 해결** (key 안정성, 렌더링 주체 격리, 상태 위치, 파생 값). `useMemo`/`useCallback`/`React.memo` 같은 메모이제이션 훅은 **사용자가 명시적으로 요청할 때만** 도입 — 측정 없이 선제적으로 추가 금지
- Existing patterns identified in `tasks.md` sub-bullets

### 2-3. Phase Completion

After implementation completes:

1. Check off completed items in `tasks.md` (`- [ ]` → `- [x]`)
2. Append an entry under `## 진행 기록` in `tasks.md`:
   ```markdown
   ### {YYYY-MM-DD}

   - Phase N: {제목} 완료 — {수정 파일 요약}
   - 블로커: {있으면}
   ```

## Step 3: Full Completion

When all Phases are done:

1. Verify all items in `tasks.md` are checked
2. Append a final entry under `## 진행 기록` summarizing completion
3. Change `tasks.md` header `상태:` field to `완료`
4. **QA guidance** — when the change includes frontend work:

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

## Communication Style

Apply the `caveman` skill to both:
- Conversational output in this flow (approach summaries, phase-completion notes, QA guidance message)
- Free-text prose appended to `tasks.md` (`## 진행 기록` entries, blocker notes)

Keep structured elements — checklists, headers, file paths, code blocks — in their normal format. Do not caveman-ify those.

## Rules

- **Do not implement without documents** — `tasks.md` and `spec.md` are required
- **Approach summary requires user approval before proceeding** — do not start writing code automatically
- **Prioritize existing patterns from tasks.md sub-bullets** — new pattern introduction requires user approval
- **Update `tasks.md` per Phase** — toggle checkboxes and append to `## 진행 기록` so handoff works even if interrupted
- **Follow `.claude/rules/react-typescript.md`** for frontend code
- **렌더링 이슈는 구조 우선 — 메모이제이션 훅(`useMemo`/`useCallback`/`React.memo`)은 사용자 명시 요청 시에만 도입**
- 산출물과 사용자 소통은 한국어로
