## Language Rules

All content written to this repository must be in English — this includes skill documents, agent documents, rules, comments in code examples, string literals, placeholders, and any other text recorded in files under `.claude/`.

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

### Use Specialized Agents for Code Changes

When the user requests code changes (implementation, modification, bug fix, refactoring — any action that creates/updates/deletes code), **always use specialized agents.**

| Work Type | Agent |
|---|---|
| Type/interface definitions, API clients, utilities, services, state management setup, data transforms | `implement-engineering` |
| Components, hooks, styling, screens, navigation, UI state handling | `implement-react` |
| Mixed (data layer + UI) | `implement-engineering` first → then `implement-react` sequentially |

> Scope and exceptions → see `/implement` skill
