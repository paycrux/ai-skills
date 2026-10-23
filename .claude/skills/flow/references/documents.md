# Documents — layout, JSON, references, viewer

Contents: layout · who writes what · task JSON · references · the viewer and saving · opening the
page · reading for tokens · legacy documents

## Layout

```
<repo>/
├ package.json                 "scripts": { "flow": "node docs/.flow/server.mjs" }   (flow.py install)
└ docs/
  ├ .flow/                     server.mjs + viewer/ — copied from the skill, never edited there
  ├ <domain>/                  one per Figma top-level section, kebab-case English (gift, account-settings)
  │ ├ domain.json              {"title", "kind": "screens|components", "figma", "nodes": [...], "paths": [...], "links": [...]}
  │ ├ screens.json             the domain's SOT map — see sot-map.md
  │ ├ tasks/<task-id>.json     one per task; the ID is the Jira key or a short English slug
  │ ├ images/                  Figma screenshots and structure XML
  │ └ prd.md                   PRD snapshot when one was fetched
  └ <anything else>            legacy — listed by the viewer, never written
```

- A domain folder is recognised by `domain.json`. `nodes` and `paths` are what `flow.py find` matches
  a new task against — add every Figma frame ID and source directory the domain covers.
- One file per task keeps two branches working on the same domain from conflicting when they merge.
  Only two tasks editing the same `screens.json` row conflict — and that is a real conflict.
- Commit everything, images included; the documents follow the code into the PR.

## Who writes what

| File | Written by | How |
|---|---|---|
| `.flow/` | `flow.py install` | re-run after a skill update |
| `domain.json`, `screens.json`, `tasks/*.json` | Claude | edit the JSON directly |
| the same files | the person, through the viewer | the server writes them on 저장, marking what changed `"by": "user"` |

## Task JSON

```json
{
  "id": "COMP-452", "title": "선물내역 · 받은 선물 목록", "type": "기능 개발",
  "branch": "feat/COMP-452", "links": [{"label": "기획서 2.3", "url": "…"}],
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

- A stage exists only if its key is present (`flow.py task --stages`, `flow.py add`). The viewer
  shows missing stages as 건너뜀.
- `status`: `done` (green) · `now` (blue) · `ask` (amber — waiting on a person) · `wait` (grey).
  At most one `now`. `grill` has no status; it is derived from its rounds.
- `summary`: one line for the nav; the viewer appends the checklist count itself.
- `conclusion`: 2–5 full sentences. A reader who reads only this must know what was decided and what
  is next. This is the only part a later stage reads.
- Block types: `text` (`html`), `quote` (`items`), `table` (`columns`, `rows`), `checklist` (`id`, `title`, `items`).
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

Write `[[ID]]` anywhere in text. The viewer turns it into a link with a hover preview, and the SOT
map shows, under each row, which task items cite it.

| ID | Points to | Scope |
|---|---|---|
| `S5`, `X3` | SOT row, off-screen state | the domain's `screens.json` |
| `R2-Q1`, `R2` | question, round | the current task |
| `P2`, `P2-1` | Phase, item | the current task |
| `V1`, `B1`, `D1` | verify item, bug, closing item | the current task |
| `COMP-451#R2-Q1` | an item in another task | same domain |
| `COMP-451` | a task | same domain |
| `login/S3`, `login/COMP-9#P1` | anything in another domain | — |

- IDs are assigned once and never renumbered or reused. A new row takes the next free number.
- Inside `screens.json` there is no current task: cite task items with the task ID (`[[COMP-451#R1-Q2]]`).
- `flow.py check` fails on a reference that points nowhere.

## The viewer and saving

`npm run flow` (or `node docs/.flow/server.mjs`) serves `docs/` at `http://127.0.0.1:<port>/`.
It starts on 4317 or the next free port, prints the URL, and reuses a server already running for
the same worktree (the port is kept in the worktree's git directory, never committed). One server
shows one worktree; run one per worktree when several are open — the nav shows repo and branch.

| URL | Shows |
|---|---|
| `/` | every domain with its open tasks, and the legacy file count |
| `/<domain>/` | the domain's tasks and SOT map |
| `/<domain>/<task>` | stages 01–06 on one page; `#P2`, `#R1-Q2`, `#tasks` jump inside it |
| `/legacy/<path>.md` | a legacy Markdown file, rendered read only |

The left nav lists every domain on every page, the current task's stages under it, and legacy files
collapsed at the bottom; the search box filters all three.

What the person can change, and what it leaves for Claude (`flow.py changes`):

| In the page | Written to the JSON |
|---|---|
| tick a checklist item | `done`, `"by": "user"` on the item |
| answer a question | `answer: {choice, note, followUp, by: "user"}` |
| double-click a conclusion line or a text block and edit it | the new text, `"by": "user"` on the stage or block |

Saving sends the file together with the fingerprint it was loaded with. If the file changed in the
meantime, the server refuses and the page keeps the edits in the browser and says so. Claude edits
the JSON directly; a page that is open picks up the change within a few seconds when it has no
unsaved edits. When the server is unreachable, the page offers 복사 — the person pastes the JSON
into chat and Claude writes it.

## Opening the page

Open only when the person has to look or act: a new or revised round, plan approval, completion.

1. Start the server in the background if it is not running: `node <docs>/.flow/server.mjs`
   (it prints the URL; a second start just prints the running one).
2. macOS: `open -a "<Google Chrome / Arc / Microsoft Edge / Safari>" http://127.0.0.1:<port>/<domain>/<task>#<anchor>`.
   Linux: `xdg-open …`. Remote sessions and other agents: print the URL.

Each `open` adds a tab; at other stops tell the person to look at the page they already have.

## Reading for tokens

- Resuming: `flow.py brief <task.json>` — stage lines, conclusions, decided questions, pending marks.
- Working on a stage: `flow.py brief <task.json> --stage tasks`, plus the JSON of that stage only.
- SOT rows: read the rows you cite from `screens.json`, not the whole file, when it is large.
- What the person changed: `flow.py changes`, then `git diff` on the files it names.

## Legacy documents

Folders and files under `docs/` without `domain.json` predate this skill (`task-plan` plans,
standalone notes). The viewer lists `.md` and `.html` files and renders Markdown read only; nothing
in this skill writes them. Cite them from a task by plain relative path, not `[[…]]`.
