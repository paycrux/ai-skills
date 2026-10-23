---
name: flow
description: "Run a frontend task from PRD to PR as linked HTML pages in docs/<task>/ — Figma SOT map, in-page question rounds, plan, build, verify. Use when the user runs /flow or hands over PRD + Figma links for a screen."
argument-hint: "<PRD link or text> [figma links] [Jira key] — or a task folder name to resume"
---

# /flow

One task becomes one folder of linked HTML pages a person can open in a browser and an agent can
read cheaply. Six stages, each a page whose first block is its **conclusion** — later stages read
only that block.

```
01 기획 → 02 화면 · SOT 맵 → 03 질문 ⇄ (02 · 04 · 05) → 04 구현 계획 · 구현 → 05 검증 → 06 완료
```

The user acts in four places only: answering questions, approving the plan, unblocking an item,
confirming completion. Everywhere else, keep going.

Read before starting:

- `${CLAUDE_SKILL_DIR}/references/documents.md` — folder, markup, who writes which file, opening pages
- `${CLAUDE_SKILL_DIR}/references/sot-map.md` — stage 02, when the task has a screen
- `${CLAUDE_SKILL_DIR}/references/questions.md` — stage 03, every time a round opens or answers arrive

`build.py` below means `python3 ${CLAUDE_SKILL_DIR}/scripts/build.py`.

## Step 0: New or resume

- The argument names an existing `docs/<task>/data/task.json` → **resume**: run `build.py check <dir>`,
  read the conclusions in `index.html`, and continue at the first stage that is `ask` or `now`.
  If `data/inbox.json` has entries, run `build.py apply <dir>` first.
- Otherwise → **new**: pick a kebab-case English task name, then
  `build.py init docs/<task> --title "<한국어 제목>" --key <JIRA-KEY> --type "<기능 개발|기능 수정|버그 수정>"`.
  Add PRD / Figma / Jira URLs to `data/task.json` → `links` as `{"label", "url"}`.

A one-file, one-decision change does not need this flow. Say so and do it directly.

## Step 1: 01 기획

Fill `01-plan.html` from the template already in place.

- Quote only the sentences this task depends on, verbatim, with their section number. Link the
  source; never paste the whole PRD.
- Conclusion: what gets built, what does not. Status `done` when written.

## Step 2: 02 화면 · SOT 맵

Follow `references/sot-map.md`. Fetch the Figma screenshot and metadata now — this is the stage the
design scan belongs to; detailed spacing and token values are still read at implementation time.

- Write `data/sot.json`, run `build.py build <dir>`, open `02-screen.html` and check every pin sits
  on its element.
- Each `pending` row becomes a question. Status `ask` while any remain, `done` when none do.

## Step 3: 03 질문

Follow `references/questions.md`. Write the round into `data/grill.json`, `build.py build`, open
`03-grill.html`, and stop:

```
화면과 데이터 흐름을 정리했어요. 확인이 필요한 3건을 질문으로 올렸어요.
열린 페이지에서 답하고 저장한 뒤 "저장했어"라고 알려 주세요.
```

On "저장했어": `build.py apply <dir>`, then handle every printed line — write decisions as full
sentences, apply them to 02 / 04, record `appliedTo`. Loop until no round is open or revised.
The page also lets the user change a decided answer later; that arrives the same way and must be
re-applied, never ignored.

## Step 4: 04 구현 계획

Write `04-tasks.html` from 02 and 03 **conclusions** (plus `data/sot.json` rows you cite).

- Phases ordered bottom-up: types · constants → data · API → state · hooks → UI → wiring. A Phase
  ends in something checkable; its last item is `검증:` with the command or screen check.
- Each item: a bold title naming what gets built, then labeled rows — `파일`, `SOT` (02 marker
  numbers), `재사용` / `패턴` from a real look at the codebase. Do not restate behavior that 02
  already holds; cite the marker.
- Explore only enough to fill `재사용` / `패턴` for every item, or to confirm nothing exists.
- Conclusion status `ask`, open the page, and stop for approval:

```
계획을 세웠어요. Phase 3개예요: 데이터 → 화면 → 화면 밖 상태.
열린 페이지에서 보시고 고칠 곳을 알려 주세요. 괜찮으면 "진행해"라고 해 주세요.
```

## Step 5: 구현

On approval set 04 to `now` and work Phase by Phase.

- After each item: `build.py tick <dir> 04-tasks.html <key>`. After each Phase: run its `검증:`
  command; a failure is fixed before the next Phase.
- An item that needs a decision nobody made (copy that exists nowhere, a field with no source):
  add a round to `grill.json`, put a `blocker` row on the item, set 04 to `ask`, and **keep doing
  every item that does not depend on it**. Ask once, when the independent work is done.
- Decisions made while building go on the item as a `결정:` row and stay after it is checked.
- Update 04's conclusion at each Phase boundary, in sentences.

## Step 6: 05 검증

Fill `05-verify.html`: one checklist item per 02 off-screen state, plus the screens' main states.

- Check each on the real screen — headless browser for web (`/browse`), simulator or device for
  apps. Tick only what you actually saw.
- A defect → a `B<n>` report in 05 (증상 · 재현 · 원인), a `B<n> 수정` item in 04, fix, re-check.
  Three failed attempts on one bug → stop and ask.
- Finish with the project's deterministic commands (typecheck, lint, tests); only exit codes count.
- Conclusion status `ask`, open the page, and stop for the user's own look at the screen.

## Step 7: 06 완료

- Rewrite 02 evidence from plan-time guesses to real `file:line`, update `base` to the current
  short SHAs, rebuild.
- List every remaining `calc` row and server or PRD request in 06.
- `build.py check <dir>` must pass. Then suggest `/git-pr`; never open the PR from this skill.
  The PR body links the folder and copies the conclusions — reviewers cannot render the HTML on GitHub.

## Communication Style

Write for a reader who has not implemented this feature and does not share your context:
background before conclusion, no unexplained internal term, one clear line instead of a paragraph
they skip, no filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what
was intended. Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to chat and to every sentence inside the pages — conclusions, decisions, `rule` and
`note` in `sot.json`. Chat messages at a stop are two or three lines plus what the user should do;
the detail is in the page.

## Rules

- **Conclusions and decisions are sentences a person can read.** Never a dotted chain of keywords
- **Never edit generated files** — `02`, `03`, `index`, nav blocks come from `data/*.json` via `build`
- **Never write `data/inbox.json`** — it holds what the user did; `apply` merges and empties it
- **A revised answer is re-applied everywhere its `appliedTo` lists** before anything else continues
- **Never invent user-facing text** — no copy in PRD or Figma means a question, with a `blocker`
- **A blocker stops only its item** — independent work continues; ask once at a natural pause
- **Read conclusions, not pages** — earlier stages' conclusion blocks plus the current page, nothing more
- **`build.py check` passes before reporting a stage done**
- **Open the browser only at a stop**, with the first Chromium-family browser found; elsewhere print the path
- **Portable by default** — when the host cannot open a browser or the browser cannot save, ask the
  same questions in chat and record the answers in `grill.json` yourself
- Pages are written in Korean; this file and the references are English
