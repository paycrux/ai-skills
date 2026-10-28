# SOT map — stage 02

The screen stage answers one question per element on a screen: **where does this value come from?**
The map belongs to the domain — `<docs>/<domain>/screens.json` — and stays current across tasks: a
task adds or changes rows and cites them (`[[S5]]`) in its `screen` conclusion and plan items.
Server field as-is, app-side transform, an action, or not decided yet. Undecided rows become
questions in stage 03. The method comes from an earlier in-house `sot-map` skill; this skill
is now its source.

Contents: when to build · given a Figma section · gather · pick elements · classify · off-screen states · screens.json ·
check · non-screen tasks

## When to build it

Build screen sections when the task draws server data on a screen. A task with no screen (a util,
a config change, a skill document) gets `flows` only — see the last section.

## Given a Figma section

A link to a Figma **section** (`<section>` at the top of `get_metadata`) holds many frames, and only
some are screens. Classify every direct child before fetching anything else:

| Kind | How to tell | In 02 |
|---|---|---|
| **Screen** | device-sized frame with the real layout (status bar, app bar, content) | its own entry in `screens`, markers on every element |
| **Overlay state** | same layout as a screen plus a `BottomSheet`, `Modal`, or dimmed layer on top | its own entry titled `<screen> · <state>`; markers only on the sheet or modal — the screen behind is already mapped |
| **External screen** | content is only images (`rounded-rectangle` image fills) — a third-party page such as an identity check | no markers; one `out` row on the screen that opens it. Modals drawn over it become off-screen rows |
| **Annotation** | not device-sized, mostly text plus component samples (often an empty or blank name) | not a screen. Take a screenshot and read it: each state it draws (empty, error copy, rejected) is an off-screen row whose evidence is `주석 <node id>` |
| **Title or decoration** | a banner or group holding the section name | ignore |

- Write the classification as the first line of 02's conclusion: `섹션 프레임 9개: 화면 1, 상태 2,
  외부 3, 주석 1, 제목 1`.
- A frame that fits none of these, or two readings of the same frame, is a question in 03 — do not
  guess which screen is the real one.
- Screenshot every screen and overlay frame; screenshot annotation frames to read them, but do not
  put them in `screens`.

## Gather

1. **Figma, two calls per screen.**
   - `get_screenshot` with `maxDimension` ≥ the frame height → save to `<domain>/images/<screen>.png`
     (`curl -f -L -o`). Figma never upscales; 1x is fine.
   - `get_metadata` on the frame → save the XML verbatim to `<domain>/images/<screen>.base.xml`.
2. **Expand components that hold a marker target.** The frame's metadata stops at component
   instances — a card shows as one box with no text nodes inside. Call `get_metadata` again on
   each instance you will put a marker in, save each to `images/<screen>.<n>.xml`, then:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py merge-xml images/<screen>.base.xml images/<screen>.1.xml ... -o images/<screen>.xml
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

A screen is one Figma frame of any size. The domain page lays a portrait frame beside its tables and a
landscape frame (wider than tall, or wider than 700px) across the page, pinned above the tables.
When the same screen has several breakpoints, add each frame as its own entry in `screens`
(`<screen>-mobile`, `<screen>-web`) and mark only what differs on the later ones — say "모바일 [[S2]]와
같아요" in `rule` rather than repeating evidence.

## Pick elements

Top to bottom: values that change, rows or sections shown conditionally, controls that do something.
Skip fixed copy (section titles, static labels) unless the label changes with state. One element per
row — the same field drawn twice in different places is two rows.

Mark the **value** node, not its label. Marker placement is computed: right edge + 14px, vertically
centered; if that collides with a neighbor (a button to the right) set `"side": "left"`; for parts packed in one
row (icon, value, clear button, action) use `"top"` or `"bottom"`, which centre the pin above or below. A node you
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

## screens.json

```json
{
  "api": "GET /v1/... -> ResponseType",
  "base": "app <short sha> · server <short sha>",
  "flows": [{"title": "<flow name>", "rows": [["<when>", "<result>"]]}],
  "screens": [{
    "id": "<screen-slug>", "title": "<screen name>", "figma": "<node id> <frame name>",
    "image": "images/<screen>.png", "metadata": "images/<screen>.xml",
    "markers": [
      {"id": "S8", "section": "<figma section>", "node": "<node id>", "side": "left", "kind": "format",
       "title": "<element>", "field": "<code>items[].receivedAt</code>",
       "rule": "<condition → result>", "note": "<evidence: file:line, Figma, [[APP-452#R1-Q2]]>"}
    ],
    "offscreen": [{"id": "X1", "state": "<state>", "when": "<when>", "shows": "<what shows>"}],
    "offscreenIntro": "<optional one line>"
  }]
}
```

- Marker IDs are `S<n>`, off-screen IDs `X<n>`, unique across the domain's screens. A new row takes
  the next free number; IDs are never renumbered or reused, so a row inserted in the middle keeps
  every existing reference valid. The pin shows the number.
- `field`, `rule`, `note` accept inline HTML (`<code>`). Write `rule` and `note` as sentences a
  reader can follow without the code — the decision rules in `SKILL.md` apply.
- A decided `pending` row changes `kind`, and its `note` cites the decision: `… ([[APP-452#R1-Q2]])`.
- The task's `screen` stage conclusion names the rows it added or changed. The domain page lists under
  each row which task items cite it — that is the history of the row.

## Check

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py build <docs>
python3 ${CLAUDE_SKILL_DIR}/scripts/flow.py check <docs>/<domain>
```

A node ID missing from the merged XML is reported with its ID — expand that instance and merge
again. Open the domain page (`<docs>/<domain>/index.html`) and hover each row: the pin must sit beside the element it describes,
not on a neighbor. Move it with `side`, or with `x`/`y` as a last resort.

## Component domains

A domain created with `--kind components` maps components instead of screens. Each entry in
`screens` is one component set (the Figma frame holding its variants); the question per part is
**what decides this** instead of where the server value comes from:

| kind | Shown as | Use when |
|---|---|---|
| `prop` | Prop | the caller passes it: label, value, error text, size |
| `slot` | Slot | the caller puts its own element there: a leading icon, a trailing button |
| `state` | State | the component decides it itself: focused, filled, pressed |
| `token` | Token | a design token decides it: border, background, text colour — values read at implementation |
| `pending` · `out` | as for screens | unknown, or not built |

- Expand one variant that shows the most parts (usually Error) and mark its parts; pins for parts
  in one row take `"side": "top"` / `"bottom"`.
- Add `"variants": [{"axis", "values", "prop", "note"}]` to the entry — one row per Figma axis
  (or per group of values that maps to the same prop). Values that the component derives itself
  (Default · Focused · Filled) map to `— (state)`.
- Off-screen states are what the code must handle that Figma does not draw: long text, two states at
  once (error + disabled), required marks on hidden layers, screen reader names, dark mode.
- Cite real usage from screen domains (`[[account-settings/S3]]`) — it is the evidence that a slot
  or prop is shaped right.
- A Figma name that looks like a typo (`GarySolid`) is a question, never copied into code silently.

## Non-screen tasks

Leave `screens` empty and write `flows`: one table per behavior, one condition per row
(`언제` / `결과`). That table is the spec. `pending` has no row form here — open questions go
straight to questions.
