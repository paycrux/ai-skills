---
name: task-plan
description: "Lightweight task planning. Writes tasks.md + spec.md under docs/{name}/plans/ from a description. Use when the user runs /task-plan or wants structured planning before implementation."
argument-hint: <task description or Jira issue number>
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# /task-plan

Write `docs/{task-name}/plans/tasks.md` + `spec.md` from the user input, then hand off to
`/implement`.

The plan is what `/implement` executes without asking again. So the bar is not "a document
exists" — it is **an implementer who was not in this conversation can carry it out.**

## Step 0: Decide whether a plan is warranted

Skip the documents and say so when the task is a one-file, one-decision change — a copy fix, a
constant, a single obvious bug. Writing a two-document plan for it costs more than the change.

> 이 작업은 계획 문서를 만들 만큼 크지 않습니다. 바로 진행할까요?

Everything else gets a plan. When unsure, plan.

## Step 1: Parse the input

Extract:

- **task name** — kebab-case English slug, used as the folder name
- **issue number** — a Jira-style key (`ABC-123`) if present anywhere in the input
- **task type** — `버그 수정` | `기능 개발` | `기능 수정`

If the input references an existing feature (`기능 수정`), find the original `docs/*/plans/` folder
and record it as a `참조:` header link. Never modify a file in the original folder.

## Step 2: Explore the codebase

The point is not to understand the whole architecture. It is to answer three questions well enough
that the implementer does not have to re-discover them:

| Question | What to look for |
|---|---|
| 이미 있는 걸 다시 만들 위험 | 같은 일을 하는 컴포넌트·훅·유틸이 이미 있는가 |
| 이 프로젝트의 방식 | 상태 관리, 데이터 페칭, 폼, 라우팅을 이 저장소가 어떤 라이브러리·패턴으로 하는가 |
| 손댈 파일의 현재 형태 | 수정 대상 파일이 지금 무엇을 하고 있는가 |

How: grep the domain keywords from the input, open the candidate files, read enough to name the
pattern. Read the actual file — a filename is not evidence that it does what its name suggests.

**Stop when** every Phase item can carry a `재사용:` or `패턴:` sub-bullet, or when you have
confirmed there is nothing to reuse. Do not keep exploring past that.

**Record findings inline** as sub-bullets under the Phase item that will use them. Never write a
separate research document — a finding the implementer has to go looking for is a finding that
gets ignored.

## Step 3: Break the work into Phases

A Phase is **a unit that can be verified when it is done** — a typecheck passes, a test runs, a
screen renders. If finishing a Phase leaves nothing checkable, it is not a Phase; it is half of one.

Order bottom-up, so that each Phase only depends on Phases before it:

```
타입·상수 → 데이터·API → 상태·훅·스토어 → UI 컴포넌트 → 화면 연결
```

Sizing:

- 3–6 items per Phase. More than that means the Phase is doing two things — split it.
- Fewer than 2 Phases means the task probably did not need a plan (back to Step 0).
- Dependencies point one direction only. If Phase 2 needs something from Phase 4, the order is wrong.

Each item names its file in backticks, and a figma node link inline when there is one. If one node
maps to several sub-areas, split it into separate items.

## Step 4: Write the two documents

Use the templates in `${CLAUDE_SKILL_DIR}/templates/`. They divide as follows, and the same content
never goes in both:

| 문서 | 담는 것 | 담지 않는 것 |
|---|---|---|
| `tasks.md` | 무엇을 어떤 순서로 만드는가 — Phase, 파일 경로, 재사용·패턴, 진행 기록 | 동작 명세 |
| `spec.md` | 무엇이 맞는 동작인가 — 화면/기능 흐름, 상태 정의, 엣지 케이스 | 구현 순서, 파일 목록 |

`spec.md` is the one `/implement` consults when the code raises a question the checklist cannot
answer. Write the flows and edge cases concretely enough to settle an argument — `로딩 중에는
버튼 비활성` is a spec, `로딩 처리` is not.

Both documents are written in Korean.

## Step 5: Hand the plan back for review

Report in this shape, then stop and wait:

```
계획을 작성했습니다.

- 문서: `docs/{name}/plans/tasks.md`, `spec.md`
- Phase {N}개: {Phase 1 제목} → {Phase 2 제목} → ...
- 확인 필요: {N}건    ← 있을 때만

검토하시고 고칠 부분을 알려주세요. 이대로 괜찮으면 `/implement {name}`으로 진행합니다.
```

Apply requested changes, then handle **Open questions** below. Suggest `/implement {name}` — never
start it from this skill.

## Open questions

Anything the plan cannot decide on its own goes in a `## 확인 필요` section in `tasks.md` — one line
per question, phrased so the answer is a choice, not an essay.

Once a question is answered, **delete the question line and keep only the decision.** Never leave
the request and its answer side by side; a reader opening the doc later needs the conclusion, not
the negotiation that produced it.

- The decision goes wherever it changes the work — the Phase task line, `spec.md`, or one line
  under `## 진행 기록` when it changes neither.
- Record the decision only, in one line. No restating the options, no "사용자 확인 완료" markers.
- When the last question is answered, delete the `## 확인 필요` section itself.

## Communication Style

Write for a reader who has not implemented this feature and does not share your context: background
before conclusion, no unexplained internal term, one clear line instead of a paragraph they skip, no
filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what was intended.

Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to conversational output in this flow and to free-text prose inside `tasks.md`/`spec.md`. Structured elements — headers, checklists, tables, file paths, figma links — keep their normal format.

## Rules

- **A Phase must be verifiable when done** — otherwise merge or split it
- **Explore before writing, and inline what you found** — a Phase item with no `재사용:`/`패턴:` line means either nothing exists to reuse, or the exploration was skipped
- **Never write the same thing in both documents** — order in `tasks.md`, behavior in `spec.md`
- **Never invent user-facing text** — 안내·동의·에러 문구가 없으면 `## 확인 필요`에 올린다
- **Do not start `/implement`** — suggest it and stop
- **Do not modify the original `plans/`** when the task type is `기능 수정`
- **Portable by default** — plain conversation for every question and report. If the host offers a
  structured question tool it may be used, but the flow must work without one
- Task type is a header field on `tasks.md`; there is no type-branching elsewhere
- Output documents are written in Korean
