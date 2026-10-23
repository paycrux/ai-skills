# SOT map — stage 02

The screen stage answers one question per element on a screen: **where does this value come from?**
Server field as-is, app-side transform, an action, or not decided yet. Undecided rows become
questions in stage 03. The method comes from the `sot-map` skill in `compose_mobile_order`
(박윤국); this skill is now its source.

Contents: when to build · gather · pick elements · classify · off-screen states · write sot.json ·
build and check · non-screen tasks

## When to build it

Build screen sections when the task draws server data on a screen. A task with no screen (a util,
a config change, a skill document) gets `flows` only — see the last section.

## Gather

1. **Figma, two calls per screen.**
   - `get_screenshot` with `maxDimension` ≥ the frame height → save to `data/<screen>.png`
     (`curl -f -L -o`). Figma never upscales; 1x is fine.
   - `get_metadata` on the frame → save the XML verbatim to `data/<screen>.base.xml`.
2. **Expand components that hold a marker target.** The frame's metadata stops at component
   instances — a card shows as one box with no text nodes inside. Call `get_metadata` again on
   each instance you will put a marker in, save each to `data/<screen>.<n>.xml`, then:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/build.py merge-xml data/<screen>.base.xml data/<screen>.1.xml ... -o data/<screen>.xml
   ```
   Do not expand instances you will not mark (repeated cards, status bars).
3. **API schema** — open the generated schema or API types the app uses and expand the response
   type to the leaves. Copy field names and optionality exactly.
4. **Server behavior** — when the server repo is available, read the code that builds the response:
   who formats display strings, when a field is null, platform differences. Record `file:line`.
   Its path is per machine: ask once, store it in `.git/flow.env` as `SERVER_REPO=...` (never committed).
5. **App code** — if the screen already exists, read the adapter that maps the response to the UI.

## Text from the screenshot, position from the metadata

Layer names are not the text on screen. A text layer named `2026.11.18까지` can render
`2026.11.18 13:00`. Read labels and values from the screenshot; use metadata only for coordinates
and for `hidden="true"` (an element the design hides in this state). A mismatch between layer name
and rendered text is itself evidence — note it, and if it changes meaning (expiry vs received time),
make the row `pending`.

## Mobile, tablet, web

A screen is one Figma frame of any size. `build.py` lays a portrait frame beside its tables and a
landscape frame (wider than tall, or wider than 700px) across the page, pinned above the tables.
When the same screen has several breakpoints, add each frame as its own entry in `screens`
(`<screen>-mobile`, `<screen>-web`) and mark only what differs on the later ones — say "same as
marker N" in `rule` rather than repeating evidence.

## Pick elements

Top to bottom: values that change, rows or sections shown conditionally, controls that do something.
Skip fixed copy (section titles, static labels) unless the label changes with state. One element per
row — the same field drawn twice in different places is two rows.

Mark the **value** node, not its label. Marker placement is computed: right edge + 14px, vertically
centered; if that collides with a neighbor (a button to the right) set `"side": "left"`. A node you
cannot reach (inside a shared component you did not expand) takes explicit `"x"`, `"y"` in frame
coordinates — say so in its `note`.

## Classify

| kind | Shown as | Use when |
|---|---|---|
| `server` | Data | drawn from a response field untouched, including server-built display strings |
| `format` | Computed | formatting, sign, unit, label mapping, hide-when-zero — no new number |
| `calc` | Computed · 계산 | the app derives a new value from two or more fields — a server request candidate; say why in `note` |
| `action` | Action | pressing it causes an effect: request, save, navigation |
| `pending` | 확인 필요 | no field, or Figma / PRD / API disagree and nobody decided |
| `out` | 범위 제외 | not built in this task — cite who decided |

Never guess a `pending` row into another kind. Every `pending` row becomes a question in 03.

## Off-screen states

List every branch the data can produce that the main frame does not show: each optional field
absent, each remaining enum value, zero/empty, loading, failure, pagination, variants that only
exist in another frame, features cut from scope. These rows become the 05 verification checklist.

## sot.json

```json
{
  "status": "done",
  "summary": "<one line for the nav>",
  "conclusion": ["<full sentence>", "<full sentence>"],
  "api": "GET /v1/... -> ResponseType",
  "base": "app <short sha> · server <short sha>",
  "flows": [{"title": "<flow name>", "rows": [["<when>", "<result>"]]}],
  "screens": [{
    "id": "<screen-slug>", "title": "<screen name>", "figma": "<node id> <frame name>",
    "image": "<screen>.png", "metadata": "<screen>.xml",
    "markers": [
      {"section": "<figma section>", "node": "<node id>", "side": "left", "kind": "format",
       "title": "<element>", "field": "<code>items[].receivedAt</code>",
       "rule": "<condition → result>", "note": "<evidence: file:line, Figma, decision>"}
    ],
    "offscreen": [["<state>", "<when>", "<what shows>"]],
    "offscreenIntro": "<optional one line>"
  }]
}
```

- `field`, `rule`, `note` accept inline HTML (`<code>`). Write `rule` and `note` as sentences a
  reader can follow without the code — the decision rules in `SKILL.md` apply.
- Markers are numbered globally across screens in file order. Stage 04 items cite these numbers.
- A decided `pending` row changes `kind`, and its `note` names the decision: `… (3 · 질문 R1-Q2)`.

## Build and check

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build.py build <task-dir>
```

A node id missing from the merged XML stops the build with its id — expand that instance and merge
again. Open `02-screen.html` and hover each row: the pin must sit beside the element it describes,
not on a neighbor. Move it with `side`, or with `x`/`y` as a last resort.

## Non-screen tasks

Leave `screens` empty and write `flows`: one table per behavior, one condition per row
(`언제` / `결과`). That table is the spec. `pending` has no row form here — open questions go
straight to 03.
