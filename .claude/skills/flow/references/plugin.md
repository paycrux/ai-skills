# Workflow and personal plugins

Read when the person asks to change how *they* work with flow — turn a stage off, rename a stage,
add a stage of their own, collect more on an existing stage, restyle their pages, keep data only they
use — or when `flow.py workflow` shows a plugin stage or an attached plugin on the task at hand.

## The three layers

flow documents are committed and read by the whole team, so what others read is fixed by the team,
and what only one person sees or does is theirs to change.

| Layer | Where | Decides |
|---|---|---|
| Core | the skill (`model.py` `CORE_STAGES`) | JSON shapes, IDs, statuses, what each stage means, every `check` rule |
| Team | `<docs>/flow.config.json` (committed) | `workflow.required` — stages nobody may turn off; `workflow.labels`; shared `style` and `hide` |
| Personal | `$FLOW_HOME/config.json` + `$FLOW_HOME/plugins/<id>/plugin.json` (not committed) | which optional stages are in their workflow, stage names, own stages, own page style, own data |

`$FLOW_HOME` defaults to `$XDG_CONFIG_HOME/flow` or `~/.config/flow`.

Core catalog, in order: `plan` · `screen` · `grill` · `tasks` · `verify` · `done` · `release`.

**A personal plugin can add and rename, never remove what the team requires.** A plugin whose
`stages.use` leaves out a required stage keeps that stage on, and `flow.py plugin check` reports it.

## Files

```jsonc
// <docs>/flow.config.json — team
{ "workflow": { "required": ["tasks", "done"], "labels": { "grill": "결정" } },
  "style": "flow.css", "hide": ["block:diagram"] }

// $FLOW_HOME/config.json — which plugins are on (a plugin folder alone does nothing)
{ "plugins": ["my-flow"] }

// $FLOW_HOME/plugins/my-flow/plugin.json
{
  "id": "my-flow",
  "stages": {
    "use": ["plan", "tasks", "verify", "done", "release"],  // the stages in my workflow; omitted = every core stage
    "labels": { "tasks": "작업 쪼개기", "my-flow:perf": "성능" }
  },
  "custom": [{
    "key": "perf",                    // the stage key becomes my-flow:perf
    "title": "성능 측정",
    "after": "verify",                // a core key or an earlier custom key; default done
    "instructions": "stages/perf.md", // what Claude does in this stage — required
    "check": "node scripts/lighthouse-gate.mjs"  // optional; must exit 0 for the stage to count as done
  }],
  "attach": [{                        // extend a core stage instead of adding one
    "stage": "verify",
    "title": "성능 측정",
    "instructions": "attach/verify-perf.md",   // what Claude also does in that stage — required
    "fields": ["score", "lcp"],                // values to collect into stages.verify.ext.my-flow
    "check": "node scripts/lighthouse-gate.mjs" // optional; must exit 0 once the stage is done
  }],
  "style": "my.css"                   // inlined after the team style, in this person's builds only
}
```

Merge rules:

- Stages in the workflow = team `required` ∪ the union of every plugin's `stages.use` (every core stage when
  no plugin sets `use`) ∪ every plugin's `custom` stages.
- Names: plugin `labels` over team `labels` over the core title. Two plugins naming one stage
  differently is reported; the later plugin wins.
- Pages are never committed, so a plugin's `style` and `labels` change only this person's pages.

## What turning a stage off does

Off takes the stage out of the person's workflow, never out of the data. flow collects the same
data for everyone, so the team, the next session and any later tool read one complete record.

- **Still the same:** the stage is created when the task needs it, filled, and held to every `check`
  rule — the 05 checklist before `prune`, the reproduction test of a `버그 수정`, decisions with
  `reason` and `appliedTo`.
- **Different for this person:** its page leaves their pages (nav, task cover), and Claude does not
  stop for them there. Every stop it goes past is one `skipped` entry on the task
  (`{"stage", "stop", "why"}` — `documents.md` § Task JSON).
- **Filled from the conversation and the code, marked as such:** a question gets the answer the
  conversation supports, or the recommended choice, with `reason.by: "inferred"`; a checklist item
  ticked without the person's look gets `"by": "inferred"` (a V item seen in a headless browser, D1–D4
  run by Claude).
- **Not collectable:** an item neither the conversation nor the code can settle gets
  `"unknown": "<what is missing>"` instead of a guess — D5 when nobody could be asked about a PR,
  L1 when no deploy is visible. It does not hold the task open; `check` lists it.
- The task cover, `brief` and `current` show how many inferred, skipped and unknown entries there
  are, so what went in without a person stays visible even though its page is gone.
- `flow.py workflow` prints such a stage as 꺼짐 · 안 멈추고 기록만.

## Plugin stages

- Key `<plugin>:<key>`. Create it like any stage: `flow.py add <task.json> my-flow:perf`. Its JSON is
  the plain stage shape (`status`, `summary`, `conclusion`, `blocks`); checklist items use `E<n>` IDs.
- Before working it, read the stage's `instructions` file — `flow.py brief <task.json> --stage
  my-flow:perf` prints its path.
- Its page is `x-<plugin>-<key>.html`. A teammate without the plugin still gets a plain page, and
  their `check` validates only the shape.
- Where the plugin is installed, `flow.py check` runs `check` for a plugin stage marked `done`, from
  the repository root, with `FLOW_TASK` (task JSON path), `FLOW_STAGE` and `FLOW_PLUGIN_DIR` set. A
  non-zero exit fails `check` and blocks `prune`.

## Attaching to a core stage

A plugin can leave a stage as it is and collect more there. Three ways a plugin shapes a stage:

| Way | The stage | Its data |
|---|---|---|
| `custom` | a new stage `<plugin>:<key>` | inside that stage |
| out of `stages.use` | stays; leaves this person's pages and stops | core data + `skipped` · inferred · `unknown` |
| `attach` | stays as it is (on or off) | core data + `stages.<stage>.ext.<plugin>` |

- Attach works whether the stage is in the person's workflow or not. Off + attach is how a plugin
  takes over a stop: grill off, and a plugin attached to grill that asks in a Slack thread — the
  questions and decisions still go into grill in the core shape, and the thread, who answered and
  when go into `stages.grill.ext.<plugin>`.
- Before working the stage, read each attached `instructions` file — `flow.py brief <task.json>
  --stage <stage>` prints them with the fields to collect.
- Collect each field into `stages.<stage>.ext.<plugin>.<field>`. Same rules as an off stage: a value
  taken from the conversation or the code without the person's look is listed in
  `ext.<plugin>.inferred`; a value nobody can collect goes into `ext.<plugin>.unknown` as
  `{"<field>": "<what is missing>"}` — never a guess. `inferred` and `unknown` are the only names
  flow reads inside a plugin's `ext`; they count on the task cover and in `brief`.
- Where the plugin is installed, `check` fails a stage marked `done` while a field is neither set nor
  `unknown`, and runs the attach `check` command (same environment as a plugin stage's).
- The person's own pages show the fields under that stage as 플러그인 · <title>; a teammate without
  the plugin sees nothing extra, and the data stays in the JSON.

## Plugin data — `ext`

A plugin keeps its own data under `"ext": {"<plugin id>": {...}}` on the task, a question or a
checklist item. flow never reads inside it: IDs and `[[refs]]` there are ignored, `prune` keeps it,
and pages do not show it. Write it with the same JSON edit + `flow.py build` as everything else.
Committed JSON is shared, so data that must stay private belongs under `$FLOW_HOME`, not in `ext`.

## When the person asks for a plugin

They speak plainly ("질문 단계는 안 쓸래", "검증 다음에 성능 측정 단계 넣어줘", "내 페이지만
다크로", "작업마다 쓴 시간 기록하고 싶어"). Translate:

1. `flow.py workflow <docs>` — what is on now, and which stages the team requires.
2. No plugin yet → `flow.py plugin new <id>` (an id they gave, or their name in kebab-case); it
   writes a `plugin.json` listing every core stage in `use` and turns it on.
3. Edit `plugin.json`:
   - off → remove from `stages.use`, and tell them its data is still collected — only the page and
     the stop go. A team-required stage is not removed: tell them in chat it is a 팀 필수
     단계 (`flow.config.json` `workflow.required`) and stays on.
   - rename → `stages.labels`.
   - more data on an existing stage ("검증 단계에 Lighthouse 점수 모으는 거 붙여줘") → an `attach`
     entry with `fields` and its `instructions` file. Prefer it over a new stage when the work
     belongs to a stage that already exists.
   - own stage → a `custom` entry, its `instructions` file written with them (what to do, what
     evidence to leave in the stage), and a `check` command when "통과" has a measurable meaning.
   - own look → `style` CSS overriding the `:root` custom properties of `assets/page.css`.
   - own data → decide the `ext.<id>` shape and say where it will be written.
4. `flow.py plugin check <docs>` must exit 0, then `flow.py build <docs>` and show the
   `flow.py workflow` output.

A change for the whole team (a stage everyone must use, a shared name) goes in `flow.config.json`
instead and is committed — say which of the two you are editing.
