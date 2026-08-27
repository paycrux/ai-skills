# Host Integration & Portability

Where a behavior belongs: a skill, an agent, a hook, or nothing at all. Read this before deciding
that "the skill should also do X".

## Contents

- [Pick the right layer](#pick-the-right-layer)
- [Agents: two different things](#agents-two-different-things)
- [Hooks: when a rule must be enforced, not requested](#hooks-when-a-rule-must-be-enforced-not-requested)
- [Portability across hosts](#portability-across-hosts)
- [Validating a skill](#validating-a-skill)

## Pick the right layer

| You want | Layer | Why |
|---|---|---|
| A named workflow the user invokes | Skill | `SKILL.md` loads on demand |
| Knowledge applied automatically when relevant | Skill with `user-invocable: false` | Model decides from `description` |
| Heavy analysis that must not pollute the main context | Subagent | Separate context window |
| A rule that must hold every time, with no model discretion | Hook | The harness runs it; the model cannot skip it |
| A constraint on one repo's code | `rules/*.md` + a pointer from `CLAUDE.md` | Applies to all work, not one command |

The distinction that matters most: **a hook is executed by the harness, a skill instruction is
followed by the model.** If the cost of the model forgetting once is high — a secret gets
committed, a temp file gets pushed — that is hook territory. If forgetting once merely produces a
worse answer, keep it in the skill.

## Agents: two different things

Do not confuse them.

**Skill-bundled agents** — `<skill>/agents/<name>.md`, described in `agent-authoring.md`. Owned by
the skill, shipped with it, invoked from its steps.

**Project/user agents** — `.claude/agents/<name>.md` (or `~/.claude/agents/`). Available to every
session in scope, listed as subagent types, invocable without any skill. Frontmatter: `name`,
`description`, optional `tools` and `model`.

Choose project agents when the role outlives one workflow (a reviewer, a domain explorer). Choose
skill-bundled agents when the role only makes sense inside that skill's steps.

A skill that fans out to several agents is buying isolated context, not speed of thought. If the
step fits in the main context, do it inline — spawning an agent costs a full prompt and returns
only text.

## Hooks: when a rule must be enforced, not requested

Hooks live in `settings.json` (user, project, or local) and fire on harness events — before or
after a tool call, on session start, on stop. They are the only way to make a rule unconditional.

Good hook candidates:

- Block a tool call that would touch a path that must never be written
- Run a formatter or typecheck after every edit
- Refuse a commit that includes a scratch file

Bad hook candidates:

- Style and tone ("write in Korean") — a hook cannot rewrite prose; this belongs in the skill
- Anything that needs judgment about the current task
- Anything that would fire on unrelated work

Two costs before you reach for one. A hook is **host-specific** — only Claude Code reads
`settings.json`, so a hook is invisible to any other agent using the same skill. And it is
**invasive to install** — `settings.json` also holds the user's own permissions and env, so a
distributed skill cannot safely write into it. Ship hooks as an opt-in example the user copies,
never as something an installer merges.

## Portability across hosts

A skill in this repository is installed into Claude Code, Cursor, **and** Codex. Anything that
only exists in one host is a portability bug, not a feature.

**Portable — safe to rely on:**

- `SKILL.md` frontmatter core: `name`, `description`, `argument-hint`
- `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`
- Shell commands, `git`, `gh`, project scripts, bundled `scripts/*.py`
- Reading and writing files under the project

**Host-specific — must be optional, with a stated fallback:**

| Feature | Note |
|---|---|
| `AskUserQuestion` | Claude Code. Fallback: ask in plain conversation and list the options |
| `Skill` tool / invoking another skill | Availability varies. Fallback: inline the steps or tell the user which command to run |
| Built-in skills (`/code-review`, `/run`, …) | Claude Code only. Fallback: do the work inline |
| MCP servers | Depends on the user's config. Fallback: a CLI or an HTTP call |
| `context: fork`, `agent:`, `effort:`, `model:` | Ignored by hosts that do not implement them — safe to set, never required for correctness |
| Hooks | Claude Code only. Never required for the skill to work |

Rule of thumb: **write the portable path as the main flow, and treat a host feature as an
accelerator on top.** A skill whose happy path needs a host-only tool is broken for two thirds of
this repository's users.

Prefer a bundled script over an MCP server when both can do the job. The script runs everywhere,
is versioned with the skill, and produces the same output on every host.

## Validating a skill

Beyond the checklist in `SKILL.md` Step 6:

- **Frontmatter parses** — the file starts with `---` and the block is valid YAML
- **`description` answers both questions** — what it does and when to trigger
- **Every bundled path resolves** — `${CLAUDE_SKILL_DIR}/...` files actually exist
- **No stale contract** — if the skill reads files another skill produces, confirm that skill still
  produces them. This is the single most common way a skill rots
- **Portable happy path** — walk the main flow assuming no MCP, no host-only tool

On Claude Code, `/skill-doctor` reports structural problems and `claude plugin eval` runs an eval
suite against a skill. Both are optional extras — a skill must be correct without them.
