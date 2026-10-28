# Plan document format

`/task-plan` writes two files per task under `docs/{task-name}/plans/`:

| File | Holds |
|---|---|
| `tasks.html` | header, 개요, 확인 필요, Phases (checklists), 진행 기록, and the 기기 확인 / QA sections other skills append |
| `spec.html` | 화면/기능 흐름, 상태 정의, 엣지 케이스, 결정이 필요한 부분 |

Each file is a standalone HTML page: one inline `<style>`, no script, no external resource. A person
opens it in a browser; an agent reads and edits the source. The templates are in
`task-plan/templates/`.

## Legacy markdown plans

Plans written before this format are `tasks.md` / `spec.md` with the same sections in markdown.

- **Find** — look for `tasks.html` first, then `tasks.md` (same for `spec`). Glob both:
  `docs/*/plans/tasks.html docs/*/plans/tasks.md`.
- **Edit in place, in the file's own format** — a legacy `tasks.md` gets markdown edits
  (`- [x]`, `## 진행 기록`, `**blocker**`). Never convert a legacy plan, and never create a
  `tasks.html` beside an existing `tasks.md`.
- A task folder has one format. If both files somehow exist, the `.html` one is the plan.

## Markup

Every grep-able marker keeps the same text in both formats. Put each header field, checklist item,
labeled row and record line on its own source line, so line-based `grep` works on HTML as it does on
markdown.

| Element | HTML | Legacy markdown |
|---|---|---|
| Header field | `<li>상태: 진행중</li>` inside `<ul class="meta">` | `> 상태: 진행중` |
| Section | `<h2>확인 필요</h2>`, `<h2>Phase 1: {단계명}</h2>`, `<h2>진행 기록</h2>` | `## 확인 필요` … |
| 개요 paragraph | `<p><strong>지금:</strong> …</p>` — one each for `지금` / `목표` / `포함` / `제외` | prose |
| Open item | `<li><input type="checkbox" disabled> <strong>{만드는 것}</strong>` inside `<ul class="checklist">` | `- [ ] {항목}` |
| Done item | `<li><input type="checkbox" checked disabled> <strong>{만드는 것}</strong>` | `- [x] {항목}` |
| Labeled row (`파일:` / `디자인:` / `재사용:` / `패턴:` / `결정:` …) | nested `<ul><li><span class="label">결정:</span> …</li></ul>` inside the item's `<li>` | indented `  - 결정: …` |
| Verification item | `<li><input type="checkbox" disabled> <strong>검증:</strong> <code>{명령}</code> — {통과 조건}</li>`, last in its Phase | `- [ ] 검증: …` |
| Question (확인 필요) | `<li><span class="qid">Q1</span><strong>{정할 것}</strong> — {배경}` inside `<ul class="questions">`, under `<h3>구현을 막는 질문</h3>` or `<h3>범위만 정하면 되는 질문</h3>` | `- [ ] {질문} — 막는 항목: …` |
| Option row | `<li><span class="opt">A</span>{선택지}</li>`, `<span class="rec">추천</span>` at the end of at most one | `A안: …` inline |
| What a question holds up | `<li><span class="blocks">막는 항목: Phase 2 …</span></li>` or `구현 영향 없음` | `— 막는 항목: …` at line end |
| Blocker marker | `— <strong class="blocker">blocker</strong>: {한 줄}` at the end of the item's title line | `— **blocker**: {한 줄}` |
| Spec flow | `<h3>{흐름 이름}</h3>` + a two-column table (`언제` / `결과`), one condition per row | `- {조건}: {트리거} → {결과}` |
| Edge case | a two-column table (`상황` / `처리`) | `- {케이스}: {처리}` |
| Decision block (spec) | `<h3>` + `<ul class="decision">` with `지금 상태:` / `왜 막히는지:` label rows and option rows | bold-labeled bullets |
| File path / identifier | `<code>src/a.ts</code>` | `` `src/a.ts` `` |
| Link | `<a href="…">node 12:34</a>` | `[node 12:34](…)` |
| Record date | `<h3>2026-10-18</h3>` followed by a `<ul>` | `### 2026-10-18` |
| Table | `<table>` with `<thead>` / `<tbody>`, inside `<div class="table-wrap">` | pipe table |

The colon stays inside the label span (`<span class="label">결정:</span>`), so `grep '결정:'` finds a
row in either format. Questions carry no checkbox: an answered question is deleted, never checked,
so a checkbox there only inflates the count.

Escape `<`, `>` and `&` in prose and code as `&lt;`, `&gt;`, `&amp;`. Use only the classes the
templates carry (`meta`, `checklist`, `questions`, `decision`, `label`, `qid`, `opt`, `rec`, `blocks`,
`blocker`, `table-wrap`); no ids, no inline styles.

## Writing for a reader

The HTML exists so a person can read the plan in a browser. Markup alone does not make it readable;
these do.

- **The item title is what gets built, nothing else.** `<strong>결제 컨텍스트 store</strong>` — not
  `결제 컨텍스트 store (<code>…</code>) — PG 결과 화면에서 꺼내기 위해 zustand로`. File, timing,
  reason and pattern each go on their own labeled row.
- **One fact per labeled row.** Two files that do the same job share a row; a file and a reason do not.
- **Rows go in reading order:** task-specific labels first (`시점:`, `파라미터:`, `값:`, `이유:` —
  pick a short noun), then `파일:`, `디자인:`, `재사용:`, `패턴:`, `결정:`.
- **Never chain several flows on one line** with `/` or `→ … →`. Split them into rows: one trigger,
  one result.
- **A question's title is the decision**, short enough to scan: `transaction_id로 무엇을 쓰나`. The
  background that makes it a question goes after an em dash, one line. Options are outcomes, not
  techniques.
- Background a reader needs before the checklist goes in 개요 `지금:`, not spread over item rows.

## Common reads

```bash
grep -rl --include=tasks.html --include=tasks.md '상태: 진행중' docs
grep -m1 -E '^> 이슈:|<li>이슈:' docs/{name}/plans/tasks.*
grep -n 'class="blocker"\|\*\*blocker\*\*' docs/{name}/plans/tasks.*
grep -c 'type="checkbox"' docs/{name}/plans/tasks.html
grep -c 'type="checkbox" checked' docs/{name}/plans/tasks.html
```

Use `grep -r --include` rather than a `docs/*/plans/tasks.md` glob: in zsh a glob with no match
aborts the whole command. Count checkboxes by `type="checkbox"`, not by the word `checked` — the
stylesheet contains `input:checked`. Plans from the older template also put a checkbox on each
확인 필요 question, so the file-wide count includes them; per-Phase counting is unaffected. Progress is counted per Phase: the checkboxes between a `Phase`
heading and the next `<h2>` (or `##`), checked over total.

## Sections other skills append

- `/implement` — `<h2>기기 확인</h2>` + a checklist (React Native / Expo)
- `/qa` — one 진행 기록 line; a `QA Fix Phase` as an ordinary Phase section
- `_shared/jira/md_to_adf.py` accepts `tasks.html` directly: `--section "## QA 가이드"` matches
  `<h2>QA 가이드</h2>` too
