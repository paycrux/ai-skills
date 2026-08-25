---
name: implement
description: "Document-driven implementation workflow. Runs the approved plan straight through — implement → verify → record, phase after phase — and stops only when the user's decision, approval, or attention is actually required."
argument-hint: "<task-folder-name or path to docs/...>"
---

# /implement — Document-Driven Implementation Workflow

Reads documents produced by `/task-plan` (`tasks.md`, `spec.md`) and executes the plan straight through.

The plan was already agreed with the user when it was written. Do not re-ask for permission to carry it out.

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

If there is interrupted work, say in one line where you are resuming from and continue. Do not ask whether to resume — an unfinished plan means the work is still wanted.

If `tasks.md` still has an unanswered `## 확인 필요` item, or `spec.md` still has a `## 결정이 필요한 부분` block from an earlier run, ask about it **now**, before any code — one message covering every open item, in the 2-4 shape. Starting a Phase that depends on an unanswered question wastes the work.

## Step 2: Implementation Loop

Work through the Phases in `tasks.md` in order, **without pausing between them**. Each Phase is implement → verify → record, and then the next Phase starts on its own. The only thing that interrupts the loop is a condition in 2-4.

### 2-1. Announce the Phase — do not ask permission

Print a short block and start working immediately. It marks progress; it is not a gate.

```markdown
## Phase N: {Phase 제목}

- **대상 파일**: {생성/수정할 파일}
- **접근**: {tasks.md sub-bullet의 재사용/패턴 + spec.md 엣지 케이스 반영 포인트}
```

- Two or three lines. Never end it with `진행할까요?` and never wait for a reply.
- Inputs: the Phase task line in `tasks.md` (file path, figma node link), its `재사용:` / `패턴:` sub-bullets, and the relevant flows/states/edge cases in `spec.md`. Explore the codebase directly only when those are missing or insufficient.
- If the announcement would say something the plan does not — a different file, a different approach — that is 2-4 territory, not an announcement.

### 2-2. Implement

Follow:

- `.claude/rules/react-typescript.md` for frontend code
- **렌더링 이슈는 구조로 먼저 해결** (key 안정성, 렌더링 주체 격리, 상태 위치, 파생 값). `useMemo`/`useCallback`/`React.memo` 같은 메모이제이션 훅은 **사용자가 명시적으로 요청할 때만** 도입 — 측정 없이 선제적으로 추가 금지
- Existing patterns identified in `tasks.md` sub-bullets

### 2-3. Verify before moving on

A Phase is not done because the code is written. Check it with whatever the project actually provides — typecheck, lint, the test command, a build — scoped to what changed. Discover the command from `package.json` scripts or the repo's config; do not invent one.

- Failure → fix it and re-run. This loop stays inside the Phase; it needs no approval.
- **Same failure twice with no progress → stop (2-4).** Do not keep patching around it.
- If the project has no such command, verify by reading the change against `spec.md` — the flows and edge cases it lists.
- Record the command and its result in `## 진행 기록` only when it actually ran. `/git-pr` transcribes those lines into the PR's 테스트 케이스 section, so an unrun claim becomes a false claim in the PR.

### 2-4. When to stop

Stop the loop only for these. Everything else — file layout, naming, helper extraction, ordering inside a Phase, fixing your own mistakes — you decide and keep going.

| 상황 | 왜 멈추는가 |
|---|---|
| 문서가 정하지 않은 결정 | API 계약이 없음, 스펙에 없는 상태 처리, 어느 화면에 붙일지 불명확 |
| 사용자 노출 문구가 PRD/spec에 없음 | 안내·동의·에러 문구는 절대 지어내지 않는다 |
| 계획 밖으로 나가야 함 | 공유 컴포넌트(`components/ui/*` 등) 수정, 새 라이브러리 도입, 계획과 다른 접근 |
| 검증이 같은 이유로 두 번 실패 | 계획이나 전제가 틀렸다는 신호 |
| 되돌리기 어려운 작업 | 마이그레이션, 데이터 삭제, 배포·외부 전송 — 실행 전에 알린다 |
| 사용자만 할 수 있는 일 | 환경변수·시크릿 값, 로그인, 권한 부여, 디자인 원본 확인 |

Stopping is two steps, in this order: **write it into `spec.md` first, then ask in the conversation.** Chat scrolls away and the next session cannot read it; the design doc is where the question survives long enough to be answered properly.

#### Step 1 — Write it into `spec.md`

Append to a `## 결정이 필요한 부분` section (create it if absent), one `###` block per open decision:

```markdown
## 결정이 필요한 부분

### {정해야 하는 것 한 줄}

- **지금 상태**: {화면·데이터·코드가 지금 어떻게 동작하는지 — 이 기능을 구현하지 않은 사람도 그림이 그려지게}
- **왜 막히는지**: {이대로 두면 사용자에게 무슨 일이 생기는지}
- **선택지**
  - A안: {무엇을 한다} → {사용자가 보게 되는 결과, 감수하는 비용}
  - B안: {무엇을 한다} → {사용자가 보게 되는 결과, 감수하는 비용}
- **추천**: {어느 쪽을, 왜}
```

How to write it:

- The reader is the person deciding, not the person who wrote the code. Describe what they can see — 화면, 문구, 데이터 — not the call stack.
- Explain any internal term in the same sentence, or leave it out. A block that needs the diff to make sense has failed.
- Each line is one or two sentences. If 지금 상태 needs a paragraph, the block is describing implementation instead of the decision.
- Options are compared by their outcome, not by their technique. `A안: 응답을 캐시한다` is not an option; `A안: 목록을 캐시해서 재진입이 즉시 뜨지만, 다른 기기에서 바꾼 내용이 최대 1분 늦게 보인다` is.
- Never write a section for something you can decide yourself. This document is for 2-4 conditions only.

> `tasks.md`의 `## 확인 필요` — 계획 단계에서 나온 한 줄짜리 질문.
> `spec.md`의 `## 결정이 필요한 부분` — 구현 중 실제로 막혀서 배경 설명이 필요한 결정.
> 같은 항목을 양쪽에 쓰지 않는다.

#### Step 2 — Ask in the conversation

Then post the short version in chat. It points at the document; it does not repeat it.

```markdown
### 확인이 필요합니다

- **막힌 지점**: {어느 파일의 무슨 작업이 멈춰 있는지}
- **필요한 것**: {사용자에게서 받아야 하는 값·결정·승인 딱 하나}
- **선택지**: {A안 — 결과} / {B안 — 결과}  ← 선택지가 있을 때만
- **추천**: {어느 쪽을 왜}
- **답을 받으면**: {바로 이어서 할 일}
- **자세한 배경**: `docs/{task-name}/plans/spec.md` → 결정이 필요한 부분
```

Rules for both steps:

- Name the one thing you need. "확인 부탁드립니다" without naming the decision is not an ask.
- Never ask a bare "이렇게 할까요?" — options and a recommendation come in the same message.
- **Do not stop the whole run for it.** Finish every part that does not depend on the answer first — later Phases included — then write every blocked decision into `spec.md` and ask once.

#### Step 3 — After the answer

Delete the `###` block from `spec.md`. In its place:

- The decision goes where it belongs in `spec.md` — 화면/기능 흐름, 상태 정의, 엣지 케이스 — as if it had been specified from the start. Keep the one line of 배경 that makes the decision make sense later; drop the options and the recommendation.
- One `결정:` line in `tasks.md` `## 진행 기록`.
- When the last block is gone, delete the `## 결정이 필요한 부분` section itself. It never carries answered items.

### 2-5. Phase Completion

1. Check off completed items in `tasks.md` (`- [ ]` → `- [x]`)
2. Append a **short** entry under `## 진행 기록` in `tasks.md`:
   ```markdown
   ### {YYYY-MM-DD}

   - Phase N 완료
   - 검증: {실행한 명령과 결과} <!-- 실제로 실행했을 때만 -->
   - 결정: {계획과 달라진 판단 + 이유 한 줄} <!-- 있을 때만 -->
   - 블로커: {있으면}
   ```
3. Start the next Phase.

**진행 기록 원칙 — 중복 금지:**
- The checklist already says what was built. Do not restate it in prose, do not list the files again, do not summarize the code.
- Record only what the checkboxes cannot carry: a verification that ran, a decision made during implementation and why, a deviation from the plan, a blocker.
- One line per item. If a Phase produced no decision and no blocker, `- Phase N 완료` alone is the whole entry.

## Step 3: Full Completion

When all Phases are done:

1. Verify all items in `tasks.md` are checked
2. Append one closing line under `## 진행 기록` — `- 전체 구현 완료`. Do not re-summarize the Phases; they are already checked off and recorded.
3. Change `tasks.md` header `상태:` field to `완료`. Delete `tasks.md`'s `## 확인 필요` and `spec.md`'s `## 결정이 필요한 부분` — a finished plan carries no open question. If either still holds an unanswered item, the work is not complete: ask instead of closing.
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

Write for a reader who has not implemented this feature and does not share your context.

- Explain the background before the conclusion. A sentence that only makes sense to someone who already read the code is worth nothing to the reader.
- Never drop an internal term without unpacking it — serialization formats, protocol details, library internals, framework behavior. Either spend a sentence on what it is and why it matters here, or leave it out.
- When the background costs more than two or three sentences to explain, compress the whole point to one line instead. One clear line beats a paragraph the reader skips.
- No filler: 전반적으로, ~등을 개선, 안정성 향상 and the like add length without information.

This applies to conversational output in this flow and to free-text prose appended to `tasks.md`. Structured elements — checklists, headers, file paths, code blocks — keep their normal format.

## Rules

- **Do not implement without documents** — `tasks.md` and `spec.md` are required
- **Run the approved plan straight through** — no per-Phase approval gate; announce the Phase and start
- **Stop only for the 2-4 conditions** — and when you do, write the background into `spec.md` `## 결정이 필요한 부분` first, then ask in chat with the 확인이 필요합니다 block
- **An answered decision leaves no question behind** — the spec block becomes spec text, the record becomes one `결정:` line
- **Verify each Phase before moving on** — and never write a verification line for a command you did not run
- **`## 진행 기록` carries verification, decisions, and blockers only** — the checklist already records what was implemented; do not write it twice
- **Prioritize existing patterns from tasks.md sub-bullets** — introducing a new library or pattern is a 2-4 stop
- **Update `tasks.md` per Phase** — toggle checkboxes and append to `## 진행 기록` so handoff works even if interrupted
- **Follow `.claude/rules/react-typescript.md`** for frontend code
- **렌더링 이슈는 구조 우선 — 메모이제이션 훅(`useMemo`/`useCallback`/`React.memo`)은 사용자 명시 요청 시에만 도입**
- 산출물과 사용자 소통은 한국어로
