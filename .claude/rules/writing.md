# Writing Rules (documents and conversation)

> The canonical version of the `## Communication Style` block that `/flow`
> and `/skill-creator` each carry a one-paragraph summary of. Edit here first.

Applies to prose written for a person to read — plan documents, progress notes, PR bodies, QA
guides, and conversational output. Structured elements (checklists, headers, tables, file paths,
code blocks, figma links) keep their normal format and are not covered here.

## The reader

**Write for someone who has not implemented this feature and does not share your context.**

That reader is real: the person reviewing the PR, the QA engineer running the guide, the teammate
picking up the plan next month, and you three weeks from now. None of them has the code loaded in
their head.

## Rules

**1. Background before conclusion.**
Start from the situation anyone can see, then the choice you made. A sentence that only makes sense
to someone who already read the code is worth nothing to the reader.

**2. Never drop an internal term without unpacking it.**
Serialization formats, protocol details, library internals, framework behavior, in-house
abbreviations. Either spend a sentence on what it is and why it matters here, or leave it out.

**3. When background costs more than two or three sentences, compress the whole point to one line.**
One clear line beats a paragraph the reader skips. This is a real trade — take the line.

**4. No filler.**
전반적으로, ~등을 개선, 안정성 향상, 가독성 향상, 코드 정리, 리팩터링 진행, 로직 수정, 기능 보완.
These add length without information. If deleting the filler leaves nothing, delete the sentence.

**5. State what is, not what was intended.**
Record what the code does and what actually ran. Intent, expected benefit, and effort spent are not
observations — leave them out.

**6. An item that carries a result or a decision is split, not packed.**
When one checklist item or bullet holds a measurement, a cause and a proposal, write it in this
order, one labeled sub-line each:

1. The headline — what happened or what has to be decided, in words a non-implementer uses.
2. What is measured — what the number means on screen or for the user, before the number itself.
3. Why — the cause, in plain words.
4. The numbers — one number per line, each labeled with what it is (normal / current limit /
   broken), so the reader sees which two are being compared.
5. The proposal — the change and what it buys.

```
❌ - [ ] 요청사항 [확인] 닫기 첫 걸음 기준 — iOS 는 첫 34ms 가 12~17% 로 기준 16.5% 에 걸림. 정상 0~17% · 회귀 34~50% 라 25% 로 올리자고 제안
✅ - [ ] 요청사항 시트를 [확인]으로 닫을 때 iOS 에서 3번 중 1번 실패 — 기준을 바꿀지 결정 필요
       - 재는 것: 닫히기 시작하고 아주 짧은 순간(34ms) 동안 얼마나 내려갔나. 많이 내려가면 "툭 떨어지는" 느낌
       - 걸린 이유: iOS 는 키보드도 같이 내려가서, 시트가 키보드를 따라 조금 더 내려감
       - 숫자 비교
         - 정상으로 닫힐 때: 최대 17%
         - 지금 기준: 16.5% ← 정상인데 걸림
         - 진짜 고장: 34% 이상
       - 제안: 기준을 25% 로 → 정상은 통과, 고장은 여전히 잡힘
```

Never join several numbers on one line with `·`, and never name a check by its internal label
(`첫 걸음`, `band`, `closedUnderFinger`) without saying what it looks like. Per-platform or per-case
results go in a small table, placed at the left margin right after the list, with a one-line
caption naming the item it belongs to. Never indent a table inside a list item — Obsidian and most
markdown viewers render it as raw `|` text.

**7. Readable means comparable — pick table or lines by shape.**
Two or more items that share the same attributes (symptom / number / cause, problem / fix,
option A / option B) go in a table: one row per item, one column per attribute. Labeled sub-lines
(rule 6) are for a single item whose shape nothing else shares. A list where every item repeats
`보이는 모습: … / 숫자: … / 결과: …` has failed — it is a table written as a list.

**8. No labels that rot, no meta lines.**
Never tag items with cross-references (`(문제 1)`, `(목표 4)`, `위 남은 일`), discovery dates
(`(11-24 발견)`), internal row IDs (`M6`) or footnote marks — they break once items move. Name the
thing in words (`아래 "닫기 판정 결과" 표`). Never write lines about how the document is kept or
read (`상태는 11-24 기준`, `위만 읽어도 결론은 나온다`).

## Structure

Applies to any document longer than a screen — plan, measurement report, retrospective, research
comparison, PR description.

- **Headings name a role, as a noun**: `문제`, `목표`, `결과`. Not questions, not two ideas joined by
  an arrow. No catch-all sections (`기타`, `새로 드러난 것`, `남은 것`) — a late finding goes where its
  role is.
- **The hierarchy is visible.** Section `##` → item `###` (each problem, each goal) → group `####`.
  A bold line is a table caption, never a stand-in for a heading. Every table has a heading or a
  caption.
- **A section opens with its summary, not a description of its table.** Start with the effect, one
  line per item (`시트 하나 판정: 84~138초 → 약 3.3초`, `결론: B 채택`), then the tables. Never write a
  sentence that only explains what a table measures.
- **Group by the reader's first axis, then the next** (device → condition, page → viewport,
  option → criterion). A flat list of more than about four items is grouped by what the reader does
  next, one table per group.
- **One list per thing.** Remaining work stays as unchecked boxes in the same checklist as the done
  work.
- **The top stands alone.** A fact the reader needs now is written there, not behind a link further
  down.

## Tables

- **A header is a promise about every cell under it.** A column named `iOS` (or `Chrome`, or
  `후보 A`) holds only that. Never mix two platforms, browsers or options in one cell.
- **One question per table.** Rows answering different questions (how fast / how reliable / does it
  pass) or in different units go in separate tables, each under its own heading or caption.
- **One attribute per column.** No catch-all headers (`숫자, 결과`, `기타`, `확인한 것`). Pick the
  attributes every row answers — for problems: `보이는 모습` / `언제 나오나` / `원인` / `상태` — and
  write `미확인` where unknown.
- **Comparisons go in columns, never in a basis line.** Never write `수치는 iOS 기준` above a table.
  - Short values (numbers): one column per side — `iOS 전 | iOS 후 | Android 전 | Android 후`.
  - Long text, or the same columns per side: one table with a second column naming the side
    (`플랫폼`, `브라우저`, `후보`), one row per side.
  - Write `안 잼` where nothing was measured and `-` where a value does not apply.
- **Merge a repeated first-column value**: write it in the first row of the group, leave the first
  cell empty in the rows after it.
- **No before → after chains inside a cell.** `A 7~23초 → 0.4~0.8초<br>B 30~60초 → 1.2~1.3초` is a
  comparison table squeezed into a cell. Numbers live in their own `전 | 후` table; a summary table
  says what changed in words and names that table.
- **Details stay in the cells.** No `표 보충` list under a table. Split a row in two when it holds
  two comparisons. Several values in one cell are separated by `<br>`, one per line, with no bullets.
- Paired comparison words: `전` / `후`, not `전` / `지금`.

## Documents that report results

Retrospectives, measurement reports, experiments, research comparisons.

- **Order by time**: `개요` → what happened in the period → the follow-up (`문제` / `목표` / `결과`)
  → `결론` → `배운 것` → optional detail log. The account of the period never mixes in later work.
- **`개요` is frozen at the end of the period it covers**: goal, whether it was met, what was done,
  what was left, the core lesson. Later work never goes in. Size stats (files, lines) stay out.
- **`결과` has a fixed shape**: `목표 달성` (`목표 | 달성 | 바뀐 것 | 남은 것`) → `측정 환경` (one
  short table) → one heading per improvement axis (`속도 개선`, `신뢰도 개선`; for research, one per
  criterion). Supporting tables (how the procedure changed, status measured with the new method) sit
  under the axis they support as captioned tables, never as headings of their own.

## Failure test

A paragraph a reader can only follow after opening the diff has failed. Delete it, or replace it
with the one line they can follow.
