## Language Rules

All content written to this repository must be in English — this includes skill documents, agent documents, rules, comments in code examples, string literals, placeholders, and any other text recorded in files under `.claude/`.

Exceptions (Korean allowed): `README.md`, `CHANGELOG.md` at the project root.

---

## Task Planning Rules

### /task-plan Skill Usage

When the user requests new feature development, bug fixes, or similar tasks, always ask first:

> "/task-plan skill을 사용해서 작업 계획을 먼저 세울까요, 아니면 바로 진행할까요?"

- If the user says no planning is needed → proceed directly
- If the user wants a plan → run `/task-plan` skill
- If the user attaches a design doc or requirements → analyze and feed into the skill flow

> Direction changes, PR creation rules, PRD update rules → see `/task-plan` skill

## Implementation Rules

### Direct Implementation (No Sub-agents)

All code changes are executed directly in the main conversation. Do not spawn sub-agents for implementation.

- Follow `.claude/rules/react-typescript.md` for frontend code
- Follow existing patterns discovered in codebase exploration
- When using `/implement`, the skill orchestrates phases — but code is written directly, not delegated
