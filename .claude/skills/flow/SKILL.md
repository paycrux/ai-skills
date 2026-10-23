---
name: flow
description: "Run a frontend task from PRD to PR as JSON documents under docs/<domain>/ that a local viewer (npm run flow) shows as linked pages — Figma SOT map per domain, question rounds answered in the page, plan, build, verify. Use when the user runs /flow or hands over PRD + Figma links for a screen."
argument-hint: "<PRD link or text> [figma links] [Jira key] — or a task ID to resume"
---

# /flow

Documents live per **domain** — one folder per Figma top-level section (선물하기, 계정 설정, 주문서) —
and every task on that domain is one JSON file inside it. A small local server shows the whole
`docs/` tree as linked pages; the person answers and checks things there and saves straight into
the JSON. Claude reads and edits the JSON.

```
01 기획 → 02 화면 · SOT 맵 → 03 질문 ⇄ (02 · 04 · 05) → 04 구현 계획 · 구현 → 05 검증 → 06 완료
```

The user acts in four places only: answering questions, approving the plan, unblocking an item,
confirming completion. Everywhere else, keep going.

Read before starting:

- `${CLAUDE_SKILL_DIR}/references/documents.md` — layout, JSON shapes, references, the viewer, saving
- `${CLAUDE_SKILL_DIR}/references/sot-map.md` — stage 02, when the task has a screen
- `${CLAUDE_SKILL_DIR}/references/questions.md` — stage 03, every time a round opens or answers arrive

`flow.py` below means `python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py`. `<docs>` is the repository's
`docs/` folder.

## Step 0: New or resume, and how big

- `<docs>/.flow/` missing → `flow.py install <docs>` (copies the server and viewer, adds
  `"flow": "node docs/.flow/server.mjs"` to `package.json`; tell the user it is a shared-repo change).
- The argument names an existing task → **resume**: `flow.py brief <task.json>`, then
  `flow.py changes <docs>/<domain>` if it reports changes, and continue at the first stage that is
  `ask` or `now`. Do not read the whole JSON.
- Otherwise → **new**. Find the domain first — never create a folder for a screen that already has one:

```bash
flow.py find <docs> --node <figma node id>   # or --name 선물 / --path src/app/gift
```

| Found | Do |
|---|---|
| A domain matches | add the task there — follow-ups, bugs, copy fixes on a shipped feature included |
| Nothing matches, the task has a screen | `flow.py domain <docs> <id> --title "<한국어>" --figma "<node · name>" --node <id> --path <dir>` |
| Nothing matches, no screen (build, deploy) | one domain per topic, same command without `--node` |
| A design system / component library (a Figma components page) | `--kind components` domain for domain-agnostic parts only; a component that follows one domain's data (an order card, a coupon row) is built in that domain until a second domain uses it |

Then create the task with only the stages it needs; add more the moment a need appears:

| The task | `--stages` | Skip this flow? |
|---|---|---|
| One file, one obvious decision (a copy fix, a constant) | — | Yes. Say so and do it directly |
| A change that does not touch what a screen gets from the server — style, copy, logic, a bug | `tasks` | |
| A screen that draws server data is built or changes what it shows | `plan,screen,tasks` | |

```bash
flow.py task <docs>/<domain> <JIRA-KEY or short-slug> --title "<한국어 제목>" --type "<기능 개발|기능 수정|버그 수정>" --stages tasks
flow.py add <docs>/<domain>/tasks/<id>.json grill        # later, when a question needs an answer
```

| When | Add |
|---|---|
| A question needs the user's answer | `grill` |
| The work turns out to change what a screen shows from server data | `screen` (and `plan` if a PRD is involved) |
| The result has to be checked on a real screen, state by state | `verify` |
| Requests to the server or PRD remain to hand over at the end | `done` |

Add PRD / Figma / Jira URLs to the task's `links` as `{"label", "url"}`.

## Step 1: 01 기획 — when `plan` exists

**Read the PRD.**
- Notion: use the host's Notion connector when one is available; otherwise
  `python3 ${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py <url> -o <docs>/<domain>/prd.md --check-auth`
  (needs `notion-cli`). Neither available → ask the user to paste the section.
- A long PRD covers many features. Save the full text to the domain's `prd.md`, list its headings,
  and read only the section(s) this task covers — never the whole document into context.
- Notion exports attachments as signed S3 URLs carrying a temporary security token. Replace each
  `<file src="…">` with the file name before saving `prd.md`; it gets committed.

**Find the matching section.** Match by name against the Figma section or frame names the user
gave (Figma `계정 설정` ↔ PRD `2-1. 계정 설정`). Then compare the two sides feature by feature:

| Found | Do |
|---|---|
| In both | In scope. Quote it |
| In the PRD section, no Figma frame (회원탈퇴 with no frame) | A scope question in 03 — never silently in or out |
| A Figma frame whose rules live in another PRD section (로그아웃 under `2-2. 설정`) | Read that section too; ask in 03 whether it belongs to this task |
| A PRD heading with no body (`SNS연동 관리 — 참고`) | A question in 03: which source is the spec — Figma annotation, another page, or nobody yet |

**Write the stage** (`stages.plan`): a `quote` block with only the sentences this task depends on,
verbatim, with their section number; user-facing copy (snackbar, modal, inline error) quoted exactly
— 02 and 04 cite it from here. Conclusion: what gets built, what does not, which scope questions are
open. Status `done` when none are open, `ask` otherwise. One Figma section bundling several
independent features for several Jira stories belongs to `/tracker`; say so before going further.

## Step 2: 02 화면 · SOT 맵 — when `screen` exists

Follow `references/sot-map.md`. The SOT map belongs to the domain (`screens.json`); the task's
`screen` stage holds only its conclusion — which rows it added or changed, cited as `[[S5]]`.
Fetch the Figma screenshot and metadata now — this is the stage the design scan belongs to; detailed
spacing and token values are still read at implementation time.

- Edit `screens.json`, run `flow.py check`, open the domain page and check every pin sits on its element.
- Each `pending` row becomes a question. Status `ask` while any remain, `done` when none do.

## Step 3: 03 질문 — whenever a question comes up

`flow.py add <task.json> grill` first if the stage does not exist. Follow `references/questions.md`:
write the round into `stages.grill.rounds`, open the task page at `#R<n>`, and stop:

```
화면과 데이터 흐름을 정리했어요. 확인이 필요한 3건을 질문으로 올렸어요.
열린 페이지에서 답하고 저장한 뒤 "저장했어"라고 알려 주세요.
```

On "저장했어": `flow.py changes <docs>/<domain>`, handle every printed line — write decisions as full
sentences, apply them to 02 / 04, record `appliedTo` — then `flow.py clear <file> --id R1-Q2 …`.
Loop until no round is open. A decided answer the user changes later arrives the same way and must
be re-applied, never ignored.

## Step 4: 04 구현 계획

Write `stages.tasks` from the conclusions of the stages that exist (plus the `screens.json` rows you
cite). For a `tasks`-only task, the conclusion carries the scope in one or two sentences.

- One `checklist` block per Phase (`"id": "P1"`), ordered bottom-up: types · constants → data · API →
  state · hooks → UI → wiring. A Phase ends in something checkable; its last item is `P<n>-V`
  `검증: …` with the command or screen check.
- Each item: a title naming what gets built, then `rows` — `파일`, `SOT` (`[[S5]] [[S6]]`),
  `재사용` / `패턴` from a real look at the codebase. Do not restate behavior the SOT map already
  holds; cite the row.
- Explore only enough to fill `재사용` / `패턴` for every item, or to confirm nothing exists.
- Status `ask`, open the task page at `#tasks`, and stop for approval:

```
계획을 세웠어요. Phase 3개예요: 데이터 → 화면 → 화면 밖 상태.
열린 페이지에서 보시고 고칠 곳을 알려 주세요. 괜찮으면 "진행해"라고 해 주세요.
```

## Step 5: 구현

On approval set `tasks` to `now` and work Phase by Phase.

- After each item set its `done: true`. After each Phase run its `검증:` command; a failure is fixed
  before the next Phase.
- An item that needs a decision nobody made (copy that exists nowhere, a field with no source):
  add a round, put a `["blocker", "[[R2-Q1]] …"]` row on the item, set `tasks` to `ask`, and **keep
  doing every item that does not depend on it**. Ask once, when the independent work is done.
- Decisions made while building go on the item as a `결정` row and stay after it is checked.
- Update the conclusion at each Phase boundary, in sentences.

## Step 6: 05 검증 — when `verify` exists

Without it, verification is the Phases' `검증:` items. Otherwise fill `stages.verify`: one item per
off-screen state (`V3`: `[[X3]] …`), plus the screens' main states.

- Check each on the real screen — headless browser for web (`/browse`), simulator or device for
  apps. Mark done only what you actually saw.
- A defect → a `B<n>` item in the 버그 checklist (증상 · 재현 · 원인 as rows), a `B<n> 수정` item in
  `tasks`, fix, re-check. Three failed attempts on one bug → stop and ask.
- Finish with the project's deterministic commands (typecheck, lint, tests); only exit codes count.
- Status `ask`, open the page, and stop for the user's own look at the screen.

## Step 7: 06 완료

With `done`, work its checklist; without it, do the same steps and record them in the `tasks` conclusion.

- Rewrite SOT evidence from plan-time guesses to real `file:line`, update `base` to the current
  short SHAs.
- List every remaining `calc` row and server or PRD request.
- `flow.py check <docs>/<domain>` must pass. Then suggest `/git-pr`; never open the PR from this
  skill. The PR body links the task and copies its conclusions — reviewers read the PR without the viewer.

## Communication Style

Write for a reader who has not implemented this feature and does not share your context:
background before conclusion, no unexplained internal term, one clear line instead of a paragraph
they skip, no filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what
was intended. Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to chat and to every sentence in the JSON — conclusions, decisions, `rule` and `note`.
Chat messages at a stop are two or three lines plus what the user should do; the detail is in the page.

## Rules

- **One domain, one folder** — find before creating; a task on an existing screen goes into that domain's `tasks/`
- **Conclusions and decisions are sentences a person can read.** Never a dotted chain of keywords
- **Reference by ID, never by path** — `[[S5]]`, `[[R2-Q1]]`, `[[COMP-451#P2]]`, `[[login/S3]]`; IDs are never renumbered or reused
- **Read the brief, not the file** — `flow.py brief`, plus `--stage <key>` for the stage at hand
- **A `"by": "user"` mark is handled, then cleared** — `changes` lists them, `clear` removes them; `check` fails while any remain
- **A revised answer is re-applied everywhere its `appliedTo` lists** before anything else continues
- **Never invent user-facing text** — no copy in PRD or Figma means a question, with a `blocker`
- **A blocker stops only its item** — independent work continues; ask once at a natural pause
- **Never write legacy documents** — anything under `docs/` outside a domain folder is read only
- **`flow.py check` passes before reporting a stage done**
- **Create a stage only when the task needs it** — `add` it at the moment the need appears, never "just in case"
- **Open the browser only at a stop**, on the server URL; elsewhere print the URL
- **Portable by default** — when the host cannot run Node or open a browser, ask the same questions
  in chat and record the answers in the JSON yourself
- Document text is Korean; this file and the references are English
