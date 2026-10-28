# Questions — stage 03

Stage 03 is both the question record and the place the user answers. Rounds live in the task's
`stages.grill.rounds`; `03-grill.html` renders them with an answer form under each question.

Contents: where questions come from · writing a round · the rounds JSON · receiving answers ·
revisions · when answers cannot come from the page

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

## Draw the cases first

A question about states — failure branches, error codes, what a screen shows per status — is
answered by looking, not by reading. Put a `cases` table above the rounds (`stages.grill.blocks`):
one row per situation the user can end up in, with what moves, where they land, and the UI they
see drawn in the app's own pieces. The person reads the whole set of cases once, sees which rows are
still open (amber), and answers below; every answer turns the row's status chip and preview live.

- One `cases` block per moment (① right after payment, ② when the detail opens, ③ when cancel is
  pressed). `title` + `sub` label the moment on the left; `lead` is one or two sentences of
  background; `subtitle` splits a moment into two tables.
- Every row gets an `id` (`C1-2`) so questions and plans cite it (`[[C1-2]]`).
- The UI cell draws, never describes: `mocks` with a `modal`, `toast`, `banner` (in-screen alert
  with rows), or a Figma `shot` saved in the domain's `images/`. Copy goes in verbatim, `\n` for
  line breaks. Mark Figma captures with `"figma": true`; a reference capture that is not the answer
  takes `"dim": true`.
- A row waiting on a question carries `"ask": "R2-Q1"` and a status chip `{"q": "R2-Q1", "label":
  "위치 답 대기"}`; settled parts are `{"state": "done", "label": "문구 정리됨"}`; a row the server
  dropped is `"gone": true`.
- Close with a `text` block, `"style": "bridge"`, saying how the moments connect.
- The app's colors come from the domain's `mockTheme` (`{"primary": "#…", "alert": "#…"}`), so the
  drawn modal looks like the app's modal.

Each question then states its case in `context` rows instead of a long `body`:
`[["케이스", "② 상세 · … [[C2-1]]"], ["지금 앱", "…"], ["디자인", "…"], ["enum", "<code>…</code>"]]`.
When the answer is copy, add `copy` (a text field) and `preview` — a mock per answer, keyed `copy`
(drawn with the typed text in place of `{copy}`) or an option value. The preview shows beside the
question and inside the case row while the person types.

```json
{"type": "cases", "id": "C2", "title": "② 발급 실패한 선물의 상세", "sub": "보낸 선물에서 그 결제를 열 때",
 "lead": "…", "columns": ["상황", "상세 화면", "하단 버튼", "상태"],
 "rows": [{"id": "C2-2", "ask": "R2-Q3",
   "cells": [{"text": "전체 발급 실패,<br>전액 환불 성공", "note": "…", "enum": ["issueFailStatus: FULL_REFUNDED"]},
             {"ui": "디자인 없음 · 참고: 취소된 선물", "figma": true, "mocks": [{"shot": {"src": "images/x.png", "alt": "…", "dim": true}}]},
             "없음"],
   "status": [{"q": "R2-Q3", "label": "기획 답 대기"}]}]}
```

Other mock shapes: `{"toast": "선물 발송이 완료되었어요."}`,
`{"modal": {"title": "…", "body": "…", "primary": "고객센터 연결", "assistive": "닫기"}}`,
`{"banner": {"body": "{copy}", "sub": "…", "rows": [["취소일시", "2026.11.18 13:12"]]}}`.

## The rounds JSON

```json
{
  "rounds": [{
    "id": "R1", "askedAt": "10/23", "from": "<what opened this round, e.g. SOT 확인 필요 [[S4]] [[S8]]>",
    "questions": [{
      "id": "Q1", "title": "<short question>",
      "said": "<trigger, quoted>", "body": "<background → problem → choice>",
      "recommendation": "<what and why>",
      "context": [["케이스", "<the case row, [[C2-1]]>"], ["지금 앱", "<what the code does>"]],
      "options": [{"value": "a", "label": "<what the user notices>"}],
      "recommended": "a",
      "copy": {"label": "<what to type>", "placeholder": "<example>"},
      "preview": {"copy": {"banner": {"body": "{copy}"}}, "a": {"toast": "<copy>"}},
      "answer": {"choice": "a", "copy": "", "note": "", "followUp": ""},
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

When the user says they answered ("답 썼어") or copied ("복사했어"):

1. `python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py pull <docs>` — or `pull <docs> --clipboard` after
   "복사했어". It writes what the page kept into the task as `"by": "user"` marks and prints them.
   Nothing found → the browser had not written it to disk yet (pull again after ten seconds) or the
   page was opened in Safari (ask for 답 복사).
   Then `flow.py changes <docs>/<domain>` lists every answer and tick with what each needs.
2. For each line:
   - **new answer** → write `decision` as sentences a person can read: what was decided, why, and
     what it costs. Never a dotted list of keywords (`A · B · C`) — that reads only to whoever wrote
     it. Then apply it where it belongs and record that in `appliedTo`:
     a SOT row → change `kind`, rewrite `rule`/`note` and cite the question (`[[APP-452#R1-Q2]]`);
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
   `flow.py build` and `flow.py check`. Report in two lines.

## Revisions after a decision

Decided rounds stay editable in the page. A changed answer on a question that already has a
`decision` shows as 답이 바뀜 · 반영 전 until you handle it: rewrite the `decision`, re-apply it
everywhere `appliedTo` lists (and anything new), then `clear`. `check` fails while any `"by": "user"`
remains — the old decision must never silently stand.

## When answers cannot come from the page

When the host cannot open a browser, or the person prefers chat, ask the same questions in chat,
write the answers into `answer` yourself (quote them, no `by`), and continue from step 2. When
`pull` finds nothing twice and the clipboard holds no flow answer either, ask the person to paste
the 답 복사 text into chat and read it the same way.
