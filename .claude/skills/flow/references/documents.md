# Documents — folder, pages, markup

Contents: folder · who writes what · the conclusion block · checklist markup · inbox.json ·
opening the page · reading for tokens

## Folder

```
docs/<task-name>/
├ index.html        overview: every stage's conclusion on one page   (generated)
├ 01-plan.html      PRD excerpt, scope                               (Claude)
├ 02-screen.html    SOT map + flows                                  (generated from data/sot.json)
├ 03-grill.html     question rounds, answer form                     (generated from data/grill.json)
├ 04-tasks.html     phases, checklist, decisions per item            (Claude)
├ 05-verify.html    off-screen state checks, bug reports             (Claude)
├ 06-done.html      closing checklist, requests to server/PRD        (Claude)
├ data/  task.json  sot.json  grill.json  inbox.json  <screen>.png  <screen>.xml
└ assets/           copied from the skill on every build
```

`<task-name>` is a kebab-case English slug. The Jira key goes in `task.json`, not the folder name.
Commit the whole folder, PNG and XML included — they are the evidence a later refresh needs.

Every page carries the same left nav (`<!-- flow:nav --> … <!-- /flow:nav -->`), rebuilt by
`build.py` into each file. Pages are standalone: no iframe, because a page opened from disk cannot
show a folder picker inside a frame.

## Who writes what

| File | Edited by | How |
|---|---|---|
| `02`, `03`, `index`, nav blocks | `build.py` | edit `data/*.json`, then `build` |
| `01`, `04`, `05`, `06` | Claude | edit the HTML directly, keeping the markup below |
| checkbox state | user (page) or Claude | page → `inbox.json` → `apply`; Claude → `build.py tick` |
| `data/inbox.json` | the page only | Claude never writes it; `apply` empties it |

## The conclusion block

The first thing in every stage page, and the only part a later stage reads:

```html
<section class="conclusion" data-status="now" data-summary="{one line}"><h2>결론</h2><ul>
<li>{full sentence: where things stand}</li>
<li>{full sentence: what is next or what is waiting}</li>
</ul></section>
```

- `data-status`: `done` (green) · `now` (blue) · `ask` (amber — waiting on a person: an open or
  revised round, a blocker) · `wait` (grey, not started). At most one `now`.
- `data-summary`: one line for the nav. `build.py` appends the checkbox count itself.
- Items: 2–5 full sentences. State what is, not what was intended. A reader who opens only this block
  must know what was decided and what is next.

## Checklist markup (04, 05, 06)

```html
<li data-key="p2-1"><label><input type="checkbox" data-check="p2-1"> <span><b>{what gets built}</b></span></label><ul>
<li><span class="label">파일:</span> <code>{path}</code></li>
<li><span class="label">SOT:</span> {02 marker numbers}</li>
<li><span class="label">결정:</span> {decision sentence} ({question id})</li>
</ul></li>
```

- `data-key` = `data-check`, unique in the file, never reused after deletion.
- Checked: `<li data-key="…" class="done">` and `<input … checked>` — use
  `build.py tick <dir> 04-tasks.html p2-1`, which keeps both in sync and refreshes the nav.
- Row labels: `파일` · `SOT` (02 marker numbers) · `재사용` · `패턴` · `결정` · `blocker`.
  A `결정` row stays after the item is checked. Remove `blocker` when its question is decided.
- Every Phase ends with a `검증:` item naming the command or screen check that proves it.

## inbox.json

Written by the page when the user checks a box or saves a round; one entry per item, the latest wins:

```json
{"entries": [
  {"type": "check", "file": "05-verify.html", "key": "s1", "done": true, "at": "..."},
  {"type": "answer", "round": "r2", "question": "q1", "choice": "b", "note": "...", "followUp": "", "at": "..."}
]}
```

Never act on the inbox by reading it directly — run `apply`, which also prints the follow-up work.

## Opening the page

Open only when the user has to look or act: the first build, a new or revised round, plan approval,
completion. Each `open` adds a tab; at other times tell the user to refresh the page instead.

| Host | Command |
|---|---|
| macOS, Chromium browser installed | `open -a "<Google Chrome / Arc / Microsoft Edge>" docs/<task>/<page>.html` |
| macOS, no Chromium browser | `open docs/<task>/<page>.html` — read-only, answers by chat |
| Linux | `xdg-open …` |
| Remote session, other agents | print the path; do not try to open |

Pick the browser once per session: the first Chromium-family app found in `/Applications`.

## Reading for tokens

- Resuming: read `index.html`'s conclusions (or run `check`) — not the stage pages.
- Working on a stage: read the conclusions of earlier stages and the whole current page only.
- `02`: read `data/sot.json`, not the generated HTML. `03`: read `data/grill.json`.
