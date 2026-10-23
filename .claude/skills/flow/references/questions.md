# Questions — stage 03

Stage 03 is both the question record and the place the user answers. Rounds live in the task's
`stages.grill.rounds`; the viewer renders them with an answer form under each question.

Contents: where questions come from · writing a round · the rounds JSON · receiving answers ·
revisions · when the page cannot save

## Where questions come from

| Source | Example | Blocks |
|---|---|---|
| SOT `pending` rows | field missing, Figma vs PRD disagree | the plan for those rows |
| Implementation | user-facing copy exists nowhere | only the items that need it — give them a `blocker` row and keep going |
| Verification | behavior is ambiguous once seen on a device | the verify item |

Never invent user-facing text to avoid a question.

## Writing a round

Ask every question whose prerequisites are settled, in one round; a question whose answer depends
on another open question waits for the next round. Three to eight questions per round.

Each question, for a reader who has not seen the code:

- `said` — what triggered it, quoted: the PRD sentence, the user's words, or the SOT row with its
  evidence (`[[S8]]`, the layer name, and the rendered text side by side).
- `body` — what happens now → what goes wrong → the choice. Full sentences. Unpack any term the
  first time. File paths go in parentheses after the sentence that explains them.
- `recommendation` — what you would do and why, one or two sentences. Required.
- `options` — only for a real multi-way choice; each `label` says what the user will notice.
  Omit for yes/no — the page shows 추천대로 / 다르게. The page always adds 더 설명해줘.
- `recommended` — the option value the page outlines in red; defaults to `"yes"`.

## The rounds JSON

```json
{
  "rounds": [{
    "id": "R1", "askedAt": "10/23", "from": "<what opened this round, e.g. SOT 확인 필요 [[S4]] [[S8]]>",
    "questions": [{
      "id": "Q1", "title": "<short question>",
      "said": "<trigger, quoted>", "body": "<background → problem → choice>",
      "recommendation": "<what and why>",
      "options": [{"value": "a", "label": "<what the user notices>"}],
      "recommended": "a",
      "answer": {"choice": "a", "note": "", "followUp": ""},
      "decision": "<full sentences: what was decided and why>",
      "appliedTo": "<every place it changed: [[S8]], [[P2-2]]>"
    }]
  }]
}
```

Round IDs are `R<n>`, question IDs `Q<n>`; together they are cited as `[[R1-Q2]]`. A round is
**open** while any question lacks `decision`. `answer` is written by the page (with
`"by": "user"`) or by Claude from a chat answer; `decision` and `appliedTo` are written by Claude.

## Receiving answers

When the user says they saved:

1. `python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py changes <docs>/<domain>` — lists every answer, tick
   and edit the person made, with what each needs. `git diff` on the named file shows the exact change.
2. For each line:
   - **new answer** → write `decision` as sentences a person can read: what was decided, why, and
     what it costs. Never a dotted list of keywords (`A · B · C`) — that reads only to whoever wrote
     it. Then apply it where it belongs and record that in `appliedTo`:
     a SOT row → change `kind`, rewrite `rule`/`note` and cite the question (`[[COMP-452#R1-Q2]]`);
     a plan item → a `결정` row on that item, remove its `blocker` row;
     behavior with no row → a `flows` row in `screens.json`.
   - **더 설명해줘** → re-ask in the next round with what was missing (usually a sketch of the
     current state or the evidence). Nothing downstream of it is unblocked.
   - **되물음** (`followUp`) → answer it in the next round's question body, or as its own question
     if it opens a new branch.
   - **a choice different from the recommendation** → settled on the user's choice; the `note` is
     the condition. Respect it in the decision text.
   - **a tick or an edited text** → read it and carry it on (a ticked verify item the person saw
     themselves stays ticked).
3. `flow.py clear <file> --id R1-Q2 --id P3-2 …` for what you handled (no `--id` clears all), then
   `flow.py check`. Report in two lines.

## Revisions after a decision

Decided rounds stay editable in the page. A changed answer on a question that already has a
`decision` shows as 답이 바뀜 · 반영 전 until you handle it: rewrite the `decision`, re-apply it
everywhere `appliedTo` lists (and anything new), then `clear`. `check` fails while any `"by": "user"`
remains — the old decision must never silently stand.

## When the page cannot save

The page saves through the local server. When the server cannot run (no Node) or the host cannot
open a browser, ask the same questions in chat, write the user's answers into `answer` yourself
(quote them, no `by`), and continue from step 2. When the server stopped mid-session, the page's
복사 button gives the edited JSON to paste into chat.
