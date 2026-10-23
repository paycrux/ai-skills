# Questions — stage 03

Stage 03 is both the question record and the screen the user answers on. Rounds live in
`data/grill.json`; `build.py` renders `03-grill.html` from it. Never edit `03-grill.html` by hand.

Contents: where questions come from · writing a round · grill.json · receiving answers · revisions ·
when the browser cannot save

## Where questions come from

| Source | Example | Blocks |
|---|---|---|
| 02 `pending` rows | field missing, Figma vs PRD disagree | the 04 plan for those rows |
| Implementation | user-facing copy exists nowhere | only the 04 items that need it — mark them `blocker` and keep going |
| Verification | behavior is ambiguous once seen on a device | the 05 item |

Never invent user-facing text to avoid a question.

## Writing a round

Ask every question whose prerequisites are settled, in one round; a question whose answer depends
on another open question waits for the next round. Three to eight questions per round.

Each question, for a reader who has not seen the code:

- `said` — what triggered it, quoted: the PRD sentence, the user's words, or the 02 row with its
  evidence (the 02 marker number, the layer name, and the rendered text side by side).
- `body` — what happens now → what goes wrong → the choice. Full sentences. Unpack any term the
  first time. File paths go in parentheses after the sentence that explains them.
- `recommendation` — what you would do and why, one or two sentences. Required.
- `options` — only for a real multi-way choice; each `label` says what the user will notice.
  Omit for yes/no — the page shows 추천대로 / 다르게. The page always adds 더 설명해줘.
- `recommended` — the option value the page outlines in red; defaults to `"yes"`.

## grill.json

```json
{
  "rounds": [{
    "id": "r1", "askedAt": "10/23", "from": "<what opened this round>",
    "questions": [{
      "id": "q1", "title": "<short question>",
      "said": "<trigger, quoted>", "body": "<background → problem → choice>",
      "recommendation": "<what and why>",
      "options": [{"value": "a", "label": "<what the user notices>"}],
      "recommended": "a",
      "answer": {"choice": "a", "note": "", "followUp": ""},
      "decision": "<full sentences: what was decided and why>",
      "appliedTo": "<every place it changed: a 02 row, a 04 item>"
    }],
    "revised": false
  }]
}
```

A round is **open** while any question lacks `decision`. `answer` is written by `build.py apply`
from the user's input; `decision` and `appliedTo` are written by Claude.

## Receiving answers

When the user says they saved:

1. `python3 ${CLAUDE_SKILL_DIR}/scripts/build.py apply <task-dir>` — merges `data/inbox.json` into
   `grill.json` and the checklists, empties the inbox, rebuilds, and prints what is left to do.
2. For each printed line:
   - **new answer** → write `decision` as sentences a person can read: what was decided, why, and
     what it costs. Never a dotted list of keywords (`A · B · C`) — that reads only to whoever wrote
     it. Then apply it where it belongs and record that in `appliedTo`:
     a 02 row → change `kind`, rewrite `rule`/`note` and cite the question id (`R1-Q2`);
     a 04 item → a `결정:` row on that item, remove its `blocker` row;
     behavior with no row → a `flows` row in 02.
   - **더 설명해줘** → re-ask in the next round with what was missing (usually a sketch of the
     current state or the evidence). Nothing downstream of it is unblocked.
   - **되물음** (`followUp`) → answer it in the next round's question body, or as its own question
     if it opens a new branch.
   - **a choice different from the recommendation** → settled on the user's choice; the `note` is
     the condition. Respect it in the decision text.
3. `build`, then `check`. Report in two lines and open the page at the next stop.

## Revisions after a decision

Decided rounds stay editable on the page. When a saved answer differs from the stored one,
`apply` sets the round's `revised: true` and the page marks it amber. Rewrite the `decision`,
re-apply it everywhere `appliedTo` lists (and anything new), then remove `revised`. `check` fails
while any round is `revised` — the old decision must never silently stand.

## When the browser cannot save

Saving needs a Chromium-based browser (Chrome, Edge, Arc) and the task folder connected once
through the page's `폴더 연결` button. Otherwise the page is read-only: ask the same questions in
chat, write the user's answers into `answer` yourself (quote them), and continue from step 2.
