# Documents — layout, JSON, references, pages

Contents: layout · who writes what · task JSON · references · the pages and answers · opening a
page · reading for tokens · legacy documents · earlier versions

## Layout

```
<repo>/docs/
  ├ index.html                 every domain and its open tasks                      (generated)
  ├ <domain>/                  one per Figma top-level section, kebab-case English (gift, account-settings)
  │ ├ domain.json              {"title", "kind": "screens|components", "figma", "nodes": [...], "paths": [...], "links": [...], "mockTheme": {...}}
  │ ├ screens.json             the domain's SOT map — see sot-map.md
  │ ├ tasks/<task-id>.json     one per task; the ID is the Jira key or a short English slug
  │ ├ images/                  Figma screenshots and structure XML
  │ ├ prd.md                   PRD snapshot when one was fetched
  │ ├ index.html               the domain's tasks and SOT map                       (generated)
  │ └ <task-id>/               index.html (every stage's conclusion) + 01-plan.html … 06-done.html (generated)
  └ <anything else>            legacy — listed on the root page, never written
```

- A domain folder is recognised by `domain.json`. `nodes` and `paths` are what `flow.py find` matches
  a new task against — add every Figma frame ID and source directory the domain covers.
- One JSON file per task keeps two branches working on the same domain from conflicting when they
  merge. Only two tasks editing the same `screens.json` row conflict — and that is a real conflict.
  A conflict inside a generated page is never resolved by hand: take either side and `flow.py build`.
- Commit everything, the generated pages and images included — a teammate opens the pages from the
  checkout or from a shared file with nothing installed.
- `docs/index.html` is written only when the file is missing or flow made it; a project that already
  has its own `docs/index.html` gets `docs/flow-index.html` instead.

## Who writes what

| File | Written by | How |
|---|---|---|
| `domain.json`, `screens.json`, `tasks/*.json` | Claude | edit the JSON directly |
| answers and ticks in those files (`"by": "user"`) | `flow.py pull` | from what the person typed in a page |
| every `.html` | `flow.py build` | after every JSON edit; never by hand |

## Task JSON

```json
{
  "id": "APP-452", "title": "선물내역 · 받은 선물 목록", "type": "기능 개발",
  "branch": "feat/APP-452", "links": [{"label": "기획서 2.3", "url": "…"}],
  "stages": {
    "plan":   {"status": "done", "summary": "…", "conclusion": ["…"], "blocks": [
                {"type": "quote", "title": "기획서 발췌", "items": [{"text": "…", "source": "2.3"}]},
                {"type": "text", "title": "디자인", "html": "Figma <code>2507:17556</code> …"}]},
    "screen": {"status": "done", "summary": "…", "conclusion": ["[[S4]] · [[S8]]을 정했어요 …"]},
    "grill":  {"rounds": [ … see questions.md … ]},
    "tasks":  {"status": "now", "summary": "Phase 3 진행 중", "conclusion": ["…"], "blocks": [
                {"type": "checklist", "id": "P1", "title": "Phase 1 · 데이터", "items": [
                  {"id": "P1-1", "title": "목록 응답 타입", "done": true,
                   "rows": [["파일", "<code>lib/api/gift.ts</code>"], ["SOT", "[[S2]] [[S3]]"]]},
                  {"id": "P1-V", "title": "검증: <code>yarn tsc</code> 통과", "done": false}]}]},
    "verify": {"status": "wait", "summary": "검증 전", "conclusion": ["…"], "blocks": [
                {"type": "checklist", "title": "화면 밖 상태 확인", "items": [{"id": "V1", "title": "[[X1]] …", "done": false}]},
                {"type": "checklist", "title": "버그", "items": []}]},
    "done":   { … PR-time checklist D1–D3 and a text block for server / PRD requests … }
  }
}
```

- A stage exists only if its key is present (`flow.py task --stages`, `flow.py add`). The pages
  show missing stages as 건너뜀.
- `status`: `done` (green) · `now` (blue) · `ask` (amber — waiting on a person) · `wait` (grey).
  At most one `now`. `grill` has no status; it is derived from its rounds.
- `summary`: one line for the nav; the page appends the checklist count itself. `[[X7]]` in it shows
  as the plain ID, not a link — put links in `conclusion`.
- `conclusion`: 2–5 full sentences. A reader who reads only this must know what was decided and what
  is next. This is the only part a later stage reads.
- Block types: `text` (`html`, `"style": "bridge"` for a tinted connecting note), `quote` (`items`),
  `table` (`columns`, `rows`), `checklist` (`id`, `title`, `items`), `cases` (`id`, `columns`,
  `rows` with drawn UI — see `questions.md` § Draw the cases first). Any block takes `sub` for a
  small line under its title. The `grill` stage may carry `blocks` too; they render above the rounds.
- Anything that compares or classifies — PRD vs Figma, frame kinds, before vs after — is a `table`,
  never a `text` block of `라벨: …<br>` lines. The first column is the row's name; `“…”` in a cell
  marks on-screen copy the same way as in quotes.
- `quote` items: `{"text", "source"}`. Consecutive items with the same `source` show under one heading,
  so use the section (`2-1 · 닉네임 변경`), not a per-line label, and keep items of a section together.
  Write a condition and its copy as `조건 → 인라인 메시지 “문구”`: text inside `“…”` is shown as
  user-facing copy, so wrap only the exact on-screen words in it.
- Item `rows` labels: `파일` · `SOT` · `재사용` · `패턴` · `결정` · `blocker` · `증상` · `재현` · `원인`.
  A `결정` row stays after the item is done. Remove `blocker` when its question is decided.
- Text fields accept inline HTML (`<code>`, `<b>`) and references.

## References

Write `[[ID]]` anywhere in text. The page turns it into a link with a hover preview, and the SOT
map shows, under each row, which task items cite it.

| ID | Points to | Scope |
|---|---|---|
| `S5`, `X3` | SOT row, off-screen state | the domain's `screens.json` |
| `R2-Q1`, `R2` | question, round | the current task |
| `P2`, `P2-1` | Phase, item | the current task |
| `V1`, `B1`, `D1` | verify item, bug, closing item | the current task |
| `C2`, `C2-1` | case table, case row | the current task |
| `APP-451#R2-Q1` | an item in another task | same domain |
| `APP-451` | a task | same domain |
| `login/S3`, `login/APP-9#P1` | anything in another domain | — |

- IDs are assigned once and never renumbered or reused. A new row takes the next free number.
- Inside `screens.json` there is no current task: cite task items with the task ID (`[[APP-451#R1-Q2]]`).
- `flow.py check` fails on a reference that points nowhere.

## The pages and answers

Every page is one self-contained HTML file: styles and script inline, Pretendard from a CDN (falls
back to the system font offline), images by relative path. Pages link to each other by relative
path, so the whole `docs/` folder works from disk, from a zip, or from another clone.

| Page | Shows |
|---|---|
| `docs/index.html` | every domain with its open tasks; legacy files at the bottom |
| `docs/<domain>/index.html` | the domain's tasks and SOT map (pins ⇄ rows, which task items cite each row) |
| `docs/<domain>/<task>/index.html` | every stage's conclusion on one page |
| `docs/<domain>/<task>/0N-<stage>.html` | one stage; `#P2-1`, `#R1-Q2`, `#S5` jump to an item |

The left nav on a task's pages lists its six stages (skipped ones dashed), the domain and the root
above them; `[` folds it. A reference preview is built into each page, so hovering works from disk.

What the person can do in a page, and how it reaches the JSON:

| In the page | Kept in the browser | Written to the JSON by `flow.py pull` |
|---|---|---|
| pick an answer, type copy, write a note or a follow-up | localStorage, on every keystroke | `answer: {choice, copy, note, followUp, by: "user"}` |
| tick a checklist item | localStorage | `done`, `"by": "user"` on the item |

- The key is `flow:<absolute path of the task's page folder>/` — one per task and worktree, shared by
  that task's six pages. The save bar shows how many entries wait, with 답 복사 and 되돌리기.
- `flow.py pull <docs>` reads the localStorage files of the Chromium browsers on this machine —
  Chrome, Aside, Arc, Dia, Edge, Brave, Vivaldi, Atlas — only keys starting `flow:` under this `docs/`,
  newest copy per task. A browser writes them to disk a few seconds after typing; when nothing is
  found, wait ten seconds and pull again. Another Chromium browser: `FLOW_BROWSER_DIRS=<its profile root>`.
- Safari and Firefox keep localStorage where it cannot be read. Their pages show a banner; the
  person presses 답 복사 and says "복사했어", and `flow.py pull <docs> --clipboard` reads the
  clipboard. The text starts `[flow 답 · <domain>/<task> · … · t=<ms>]` and is readable in Slack too.
- `pull` records the newest copy's time as the task's `pulledAt`. A page built after that drops the
  browser copy it already gave, so the page then shows what Claude wrote.
- The person never edits conclusions or text in the page; changes to wording come through chat.

## Opening a page

Open only when the person has to look or act: a new or revised round, plan approval, completion.
Build first, then open the file in the OS default browser — never name a browser: macOS
`open <docs>/<domain>/<task>/03-grill.html`, Linux `xdg-open …`, Windows `start "" …`. Open the
page file itself and name the item to look at in chat (`R2-Q1`). Remote sessions and other agents:
print the path.

Each `open` adds a tab; at other stops tell the person to reload the page they already have.

To screenshot a page headless (playwright and similar), serve the folder — `python3 -m http.server
<port> -d <docs>` — and load `http://localhost:<port>/<domain>/<task>/03-grill.html`. A `file://`
load comes back blank.

## Reading for tokens

- Resuming: `flow.py brief <task.json>` — stage lines, conclusions, decided questions, pending marks.
- Working on a stage: `flow.py brief <task.json> --stage tasks`, plus the JSON of that stage only.
- SOT rows: read the rows you cite from `screens.json`, not the whole file, when it is large.
- What the person changed: `flow.py pull`, then `flow.py changes`, then `git diff` on the files it names.
- Never read a generated page to learn the state — the JSON holds it.

## Legacy documents

Folders and files under `docs/` without `domain.json` predate this skill (`task-plan` plans,
standalone notes). The root page lists `.md` and `.html` files; nothing in this skill writes them.
Cite them from a task by plain relative path, not `[[…]]`.

## Earlier versions

`flow.py migrate <docs>` runs at the start of the first `/flow` in a repository, and `check` fails
until it is done.

| Version | Recognised by | What `migrate` does |
|---|---|---|
| v2 — local server | `docs/.flow/server.mjs`, `"flow"` in `package.json`, `flow-server.json` in the git dir | lists the three and the new page paths; deletes them only with `--apply`, after the user agrees. The domain JSON is already current and is rebuilt as pages |
| v1 — task folders | `docs/<task>/data/task.json` beside `01-plan.html` … | lists the folder and the domain its Figma node matches; convert with `--v1` |

`flow.py migrate <docs> --v1 <docs>/<old-task> --domain <id> [--title "…"]` converts one folder:

- `data/sot.json` → the domain's `screens.json`: screens appended, markers take the next free `S`
  numbers (the old pin numbers are printed as `1→S18 …`), off-screen rows become `X` rows, images
  copied into `images/`.
- `data/grill.json` → `grill` rounds with IDs upper-cased (`r1-q2` → `R1-Q2`).
- `01` · `04` · `05` · `06` → stages: the conclusion block, `<h2>` sections as `checklist` blocks
  (`li[data-key]` items, `파일:` rows) or `text` blocks. Pages still holding only the template are skipped.
- `data/inbox.json` answers and ticks nobody applied → `"by": "user"` marks.
- The old folder is deleted when git has it committed and clean; otherwise it stays and is reported.

Then, before continuing:

1. Rewrite what still uses the old numbering — `SOT: 2번, 3번` → `SOT: [[S19]] [[S20]]` using the
   printed map, plain question numbers → `[[R1-Q2]]`.
2. Turn `text` blocks that are really tables or quotes into `table` / `quote` blocks.
3. `flow.py changes` for the inbox marks, `flow.py build`, `flow.py check`.
