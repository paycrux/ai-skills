---
name: tracker
description: "One entry point for a feature that spans several Jira issues. Reads a lump of planning links once, splits it into scopes, then on every later run works out where the work stands and does the next thing — worktree, plan, implement, verify — updating the meta-plan itself. Use when the user runs /tracker, or hands over Notion + Jira + Figma links for multi-issue work."
argument-hint: "[notion url] [jira links] [figma links] — or nothing, to continue where it left off"
---

# /tracker — 진입점 하나

A feature that spans several Jira issues turns into the same seven steps per issue: read the
planning doc, make a worktree, plan, implement, verify, then update the tracking document by hand.
Six of those seven are memory and typing. Only the implementation needs a person.

This skill is that loop. The user types the same command every time; the skill works out where the
work stands and does the next thing.

```
/tracker <노션> <지라들> <피그마>   ← 처음 한 번
/tracker                            ← 그 다음부터 계속 이것만
```

**The user never edits the meta-plan.** Every field in it is written by this skill. If a person has
to open it to fix a status, this skill has failed.

## Every run does the same four things

1. Work out the state — from files, not from what a previous run claimed
2. Do the one thing that state calls for
3. Write the result into the meta-plan
4. Stop only when a person actually has to decide

## Step 1: Find the work

- **Arguments contain links** → new work. Go to state **A**.
- **No arguments** → find `docs/*/meta-plan.md` whose 범위 table still has a row that is not `완료`.
  If several match, list them and ask which. If none, say so and stop.

## Step 2: Work out the state

Read the meta-plan's 범위 table, then check the filesystem. **The filesystem wins.** A row saying
`구현` whose `plans/tasks.md` does not exist means an earlier run died mid-way — correct the row
first, then carry on from what is actually there. Self-correction is silent; it is not worth a
paragraph to the user.

Take the first row that is not `완료` **and** whose 선행 rows are all `완료`. That is the current
scope. One scope at a time.

| 관측 | 다음 | 아래 |
|---|---|---|
| `meta-plan.md` 없음 | 기획서를 갈라 문서를 씀 | A |
| 워크트리 정책이 헤더에 없음 | 일괄/순차를 물음 | B |
| 이 범위의 워크트리·브랜치 없음 | 워크트리 생성 | B |
| `plans/tasks.md` 없음 | `/task-plan` | C |
| `tasks.md`에 `## 확인 필요` 남음 | 그것만 사용자에게 물음 | — |
| 체크 안 된 항목 있음 | `/implement` | D |
| 전부 체크됨, `qa-report.md` 없음 | `/qa` | E |
| 이 범위 `완료`, 남은 범위 있음 | PR 안내 후 다음 범위로 | F |
| 모든 범위 `완료` | 마무리 보고 | F |

## A. 기획서를 범위로 가르기

Sort the links into 기획서 / 지라 / 디자인. Derive `{name}` — a kebab-case English slug from the
Notion title — and confirm it before writing anything.

**기획서 가져오기**

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url>" \
  --output /tmp/tracker-source.md --metadata /tmp/tracker-source.json --check-auth
```

Split on `## ` headings **ignoring leading whitespace** — a Notion column layout indents its
headings, and an anchored `^## ` match finds none of them.

**이슈 읽기**

```bash
acli jira workitem view <KEY> --fields summary,issuetype,status,description --json
```

**디자인 읽기 — 얕게만.** `get_metadata` for node names; `get_screenshot` only when a name is
useless (`Frame 427`). **Never `get_design_context`** — dimensions and colors are read from the
original at implementation time, and a number copied into a planning document becomes the number
someone builds from.

**범위 가르기.** Usually one scope per issue: the part of the 기획서 that issue delivers, plus the
design nodes it renders. The 기획서 often states the split itself — a table of contents, a callout
listing its sections. Read that before inferring one.

Then report both gaps. They are the reason this document exists, because a person reading a lump
misses exactly these:

- 기획 섹션에 붙는 이슈가 없다 → 이슈가 빠졌거나 이번 범위가 아니다
- 이슈에 붙는 기획이 없다 → 기획서에 없는 것을 구현하려는 중이다

**사용자 노출 문구는 범위마다 표로 따로 뽑는다.** 스낵바·모달·버튼·에러 문구를 원문 그대로. A
spec doc scatters dozens of these through its prose, and prose is where they get missed. Never
paraphrase one, never invent one — 없으면 그 범위의 `미정`에 올린다.

Write `docs/{name}/meta-plan.md` from `${CLAUDE_SKILL_DIR}/templates/meta-plan.template.md`, in
Korean. Quote the 기획서; do not summarize it. Each scope keeps the anchor link back to its source.

Then **stop** and hand it back:

```
메타 플랜을 작성했습니다.

- 문서: `docs/{name}/meta-plan.md`
- 범위 {N}개: {범위 1} → {범위 2} → ...
- 어디에도 안 붙은 기획: {N}건    ← 있을 때만
- 기획이 없는 이슈: {N}건          ← 있을 때만
- 미정: {N}건                      ← 있을 때만

검토하시고 고칠 부분을 알려주세요. 이대로 괜찮으면 `/tracker`로 이어갑니다.
```

## B. 워크트리

**정책을 한 번만 묻는다.** Ask right after the document is approved, then record the answer in the
`워크트리:` header field and never ask again.

> 워크트리를 어떻게 만들까요?
> - 일괄 — 범위 {N}개를 지금 다 만듭니다. 각각 세션을 따로 열어두고 오갈 수 있습니다.
> - 순차 — 차례가 된 범위만 만듭니다. 브랜치와 디스크가 깔끔합니다.

**만들기 — orca 우선:**

```bash
orca worktree create --name "<이슈키>" --repo "path:$(git rev-parse --show-toplevel)" \
  --base-branch "<기본 브랜치>" --json
```

Read `path` and `branch` out of the JSON. If `orca` is not on PATH, fall back to git and prefer
순차 — without orca each worktree has no session of its own, so a batch of them is just clutter:

```bash
git worktree add "../$(basename "$PWD")-<이슈키>" -b "feature/<이슈키>"
```

Base branch: `develop` when the repo has one, otherwise the default branch. Confirm once per repo.

Write `브랜치` into the row. Then enter the worktree — the rest of this scope's work happens there.

## C. 계획

Call `/task-plan` with the scope. Feed it the scope block from the meta-plan — 이슈, 기획 앵커,
디자인 링크, 하는 일, 사용자 노출 문구 표, 미정 항목 — so it does not re-read the whole 기획서.

`/task-plan` ends by handing its plan back for review and stopping. That stop is kept: it is a real
decision, not a step to skip. Surface it, and continue when the user approves.

Write the `계획` column (`docs/<slug>/plans/`) and set the row to `계획`.

## D. 구현

Call `/implement` with the plan folder. It runs the phases straight through and stops on its own
2-4 conditions. Set the row to `구현` when it starts.

Do not re-implement anything `/implement` handles. This skill's job here is only to start it and to
record what came out.

## E. 검증

Call `/qa` with the plan folder. Set the row to `검증`.

- 통과 → row becomes `완료`
- 버그가 남음 → `/qa` writes them into `qa-report.md` and connects back to `/implement`. Stay on
  this scope until they are cleared.

## F. 마무리와 다음 범위

`/git-pr` cannot be called from a skill (`disable-model-invocation: true`) — tell the user to run it:

```
범위 {N} `{이름}` 완료 — 브랜치 `{브랜치}`
PR은 그 워크트리에서 `/git-pr`을 실행해 주세요.

다음: 범위 {M} `{이름}`    ← 남은 범위가 있을 때
`/tracker`로 이어갑니다.
```

When every row is `완료`, report the whole set — 범위별 브랜치와 계획 문서 경로 — and stop.

## 문서 갱신 — 언제 무엇을

The meta-plan is only trustworthy if this is mechanical. Each write has a file behind it, so a
missed write shows up as a mismatch on the next run and gets corrected there.

| 시점 | 쓰는 것 | 근거 |
|---|---|---|
| 워크트리 생성 직후 | `브랜치` | `orca worktree list` / `git worktree list` |
| `/task-plan` 승인 직후 | `계획`, 상태 `계획` | `plans/tasks.md` 존재 |
| `/implement` 시작 | 상태 `구현` | 체크된 항목 수 |
| `/qa` 시작 | 상태 `검증` | `qa-report.md` 존재 |
| `/qa` 통과 | 상태 `완료` | 미해결 버그 없음 |

`## 기록` gets one line per event — 무엇을 했는지만. The table already carries the state; do not
write it twice.

## 멈추는 조건

Everything else runs through without asking.

| 상황 | 왜 |
|---|---|
| 메타 플랜 작성 직후 | 범위 가르기가 틀리면 뒤가 전부 틀린다 |
| 워크트리 정책 (최초 1회) | 되돌리기 번거롭다 |
| `## 확인 필요` / `## 결정이 필요한 부분` | 기획서가 정하지 않은 것 |
| `/task-plan` 검토 | 계획 스킬 자체의 게이트 |
| `/implement`의 2-4 조건 | 구현 스킬 자체의 게이트 |
| 상태와 파일이 어긋나고 원인이 불분명 | 추측으로 덮으면 손실이 난다 |

## Rules

- **사람은 메타 플랜을 고치지 않는다** — 모든 칸은 이 스킬이 쓴다
- **상태는 파일에서 읽는다** — 이전 실행이 뭐라고 적었든 파일이 우선
- **한 번에 한 범위** — 병렬 실행은 하지 않는다. 워크트리를 일괄로 만들어도 진행은 하나씩
- **기획서는 발췌하고 요약하지 않는다** — 요약본이 생기면 어느 쪽이 진짜인지 알 수 없다
- **사용자 노출 문구는 지어내지 않는다** — 없으면 `미정`에 올린다
- **디자인은 얕게만 읽는다** — `get_design_context`는 구현 시점 전용
- **기존 스킬이 하는 일을 다시 하지 않는다** — 계획은 `/task-plan`, 구현은 `/implement`, 검증은 `/qa`
- **Portable by default** — 모든 질문과 보고는 평문 대화로. 호스트가 구조화된 질문 도구를 주면 써도 되지만, 없어도 동작해야 한다
- 산출물과 사용자 소통은 한국어

## Communication Style

Write for a reader who has not implemented this feature and does not share your context: background
before conclusion, no unexplained internal term, one clear line instead of a paragraph they skip, no
filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what was intended.

Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to conversational output and to free-text prose inside `meta-plan.md` — `전체 범위`,
`하는 일`, gap 판단 근거, `## 기록` lines. Tables, headers, links, and quoted 기획서 text keep their
normal format; quoted text is source material and is never rewritten to fit these rules.
