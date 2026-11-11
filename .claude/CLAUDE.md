## Language Rules

All content written to this repository must be in English — this includes skill documents, agent documents, rules, comments in code examples, string literals, placeholders, and any other text recorded in files under `.claude/`.

Exceptions (Korean allowed): `README.md`, `CHANGELOG.md` at the project root, and all skill output templates (`templates/*.md`) and inline output examples in `SKILL.md`.

---

## Task Planning Rules

### Entry Judgment

When the user requests a feature, a bug fix, or similar work, pick the path from the request — do not ask whether to plan:

- PRD or Figma link, or several screens or files → `/flow`
- Several Jira stories → a `/flow` feature document (`flow/references/feature.md`)
- Everything else → proceed directly and report the change in one line

> Direction changes and PRD update rules → see `/flow` skill

## Implementation Rules

### Direct Implementation (No Sub-agents)

All code changes are executed directly in the main conversation. Do not spawn sub-agents for implementation.

- Follow `.claude/rules/react-typescript.md` for frontend code
- Follow existing patterns discovered in codebase exploration
- When using `/flow`, the skill orchestrates phases — but code is written directly, not delegated
