# Personal settings

Read when the person asks to change how *they* work with flow — add a stage of their own, collect
more on an existing stage, add a feature of their own (an export, a sync to a notes app), rename a
stage, restyle their pages, keep data only they use — or when `flow.py workflow` shows an own stage,
an attachment or a command on the task at hand.

## The rules

1. **Every core stage is required.** Nobody turns one off — not the team, not a person. `off` and
   `workflow.required` are no longer read; `flow.py workflow` flags them so they get deleted.
2. **Personal settings only extend.** They add (own stages, attachments, own data, commands) and
   change what only this person sees (labels, style). They never remove or reshape a core stage.
3. **A task reads the same without the settings.** Whatever a setting writes into a task carries its
   own title, so a teammate without the file sees the same stages and data by name and edits the
   task freely. The settings decide only what more to collect and check, on this person's machine.

## Two files

| File | Committed | Decides |
|---|---|---|
| `<docs>/flow.config.json` | yes | `workflow.labels`; shared `style` and `hide` |
| `$FLOW_HOME/config.json` | no | own stages, attachments, commands, stage names, own page style |

`$FLOW_HOME` defaults to `$XDG_CONFIG_HOME/flow` or `~/.config/flow`. Everything else — JSON shapes,
IDs, statuses, what each core stage means, every `check` rule — is fixed by the skill.

Core stages, in order: `plan` · `screen` · `grill` · `tasks` · `verify` · `done` · `release`.

```jsonc
// <docs>/flow.config.json — team
{ "workflow": { "labels": { "grill": "결정" } }, "style": "flow.css", "hide": ["block:diagram"] }

// $FLOW_HOME/config.json — this person
{
  "id": "hyunsu",                     // names own stages (hyunsu:perf) and attached data (ext.hyunsu)
  "labels": { "tasks": "작업 쪼개기", "hyunsu:perf": "성능" },
  "custom": [{
    "key": "perf",                    // the stage key becomes hyunsu:perf
    "title": "성능 측정",
    "after": "verify",                // a core key or an earlier custom key; default done
    "instructions": "stages/perf.md", // what Claude does in this stage — required, relative to $FLOW_HOME
    "check": "node scripts/lighthouse-gate.mjs"  // optional; must exit 0 for the stage to count as done
  }],
  "attach": [{                        // extend a core stage instead of adding one
    "stage": "verify",
    "title": "성능 측정",
    "instructions": "attach/verify-perf.md",   // what Claude also does in that stage — required
    "fields": ["score", "lcp"],                // values to collect into stages.verify.ext.hyunsu
    "check": "node scripts/lighthouse-gate.mjs" // optional; must exit 0 once the stage is done
  }],
  "commands": [{                      // features of the person's own
    "name": "obsidian",
    "title": "옵시디언에 복사",
    "run": "rsync -a --include='*/' --include='*.json' --exclude='*' \"$FLOW_DOCS/\" ~/vault/flow/",
    "on": "build"                     // build: after every flow.py build · ask (default): flow.py run only
  }],
  "style": "my.css"                   // inlined after the team style, in this person's builds only
}
```

- `id` is required once `custom` or `attach` is used.
- Names: personal `labels` over team `labels` over the core title. `labels` rename only — this
  person's pages; the task JSON keeps the keys.
- `style` overrides the `:root` custom properties of `assets/page.css`. Pages are never committed, so
  `style` and `labels` change only this person's pages.
- `flow.py workflow <docs>` lists every stage (all `코어 · 필수`, own stages `내 단계`), attachments
  and commands, and exits 1 on any bad entry.

## Own stages

- Key `<id>:<key>`. Create it like any stage: `flow.py add <task.json> hyunsu:perf`. The skeleton
  carries `"title"` from the setting; keep it — `check` asks for it on this person's machine. Its
  JSON is otherwise the plain stage shape (`status`, `summary`, `conclusion`, `blocks`); checklist
  items use `E<n>` IDs.
- Before working it, read its `instructions` file — `flow.py brief <task.json> --stage hyunsu:perf`
  prints the path.
- Its page is `x-<id>-<key>.html`. A teammate without the setting gets the same page, titled from
  the task, and their `check` validates only the shape.
- On this person's machine, `flow.py check` runs `check` for an own stage marked `done`, from the
  repository root, with `FLOW_TASK` (task JSON path), `FLOW_STAGE` and `FLOW_CONFIG_DIR` set. A
  non-zero exit fails `check` and blocks `prune`.

## Attaching to a core stage

| Way | The stage | Its data |
|---|---|---|
| `custom` | a new stage `<id>:<key>` | inside that stage |
| `attach` | stays as it is | core data + `stages.<stage>.ext.<id>` |

- Before working the stage, read each attached `instructions` file — `flow.py brief <task.json>
  --stage <stage>` prints them with the fields to collect.
- Write `stages.<stage>.ext.<id>.title` (the attachment's title) and collect each field into
  `stages.<stage>.ext.<id>.<field>`. A value taken from the conversation or the code without the
  person's look is listed in `ext.<id>.inferred`; a value nobody can collect goes into
  `ext.<id>.unknown` as `{"<field>": "<what is missing>"}` — never a guess. `title`, `inferred` and
  `unknown` are the only names flow reads inside `ext`.
- On this person's machine, `check` fails a stage marked `done` while a field is neither set nor
  `unknown`, or while `title` is missing, and runs the attach `check` command (same environment as
  an own stage's).
- Every page shows what a stage's `ext` holds as 붙임 · <title>, with or without the setting. The
  setting only adds the fields still missing (아직 없어요).

## Own commands

A feature of the person's own — an export in their format, a sync to Obsidian or Notion, a report —
is a command, not a stage. It reads the documents and never writes into them.

- `flow.py run <docs> <name> [--task <task.json>]` runs it from the repository root with
  `FLOW_DOCS` (docs folder), `FLOW_CONFIG_DIR` and, with `--task`, `FLOW_TASK` set.
- `"on": "build"` also runs it after every `flow.py build`. A failure is printed, never fails the
  build.
- A command that writes into a task JSON is a stage or an attachment instead — say so and set that up.

## Own data — `ext`

A person keeps their own data under `"ext": {"<id>": {...}}` on the task, a question or a checklist
item. flow never reads inside it except as above: IDs and `[[refs]]` there are ignored and `prune`
keeps it. Committed JSON is shared, so data that must stay private belongs under `$FLOW_HOME`.

## When the person asks

They speak plainly ("검증 다음에 성능 측정 단계 넣어줘", "검증 단계에 Lighthouse 점수 모으는 거
붙여줘", "build할 때마다 옵시디언으로 복사해줘", "내 페이지만 다크로", "작업마다 쓴 시간 기록하고
싶어"). Translate:

1. `flow.py workflow <docs>` — what is set now.
2. Edit `$FLOW_HOME/config.json` (create it when missing; set `id` to a name they gave, or their name
   in kebab-case):
   - turn a stage off or skip it for good → refuse: every core stage is required. Offer what fits —
     a rename, or for the question stage, answering in the page or in chat as usual.
   - rename → `labels`.
   - more data on an existing stage → an `attach` entry with `fields` and its `instructions` file.
     Prefer it over a new stage when the work belongs to a stage that already exists.
   - own stage → a `custom` entry, its `instructions` file written with them (what to do, what
     evidence to leave in the stage), and a `check` command when "통과" has a measurable meaning.
   - own feature that reads the documents (export, sync, report) → a `commands` entry; `on: "build"`
     when it should follow every build.
   - own look → `style`.
   - own data → decide the `ext.<id>` shape and say where it will be written.
3. `flow.py workflow <docs>` must exit 0, then `flow.py build <docs>` and show its output.

A change for the whole team (a shared name) goes in `flow.config.json` and is committed — say which
of the two you are editing.
