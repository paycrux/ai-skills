## Task Planning Rules

### /task-plan Skill Usage

When the user requests new feature development, bug fixes, or similar tasks, always ask first:

> "/task-plan skill을 사용해서 작업 계획을 먼저 세울까요, 아니면 바로 진행할까요?"

- If the user says no planning is needed → proceed directly
- If the user wants a plan → run `/task-plan` skill
- If the user attaches a design doc or requirements → analyze and feed into the skill flow

### Task-plan Document Sync

If the root cause or approach diverges from the task-plan during implementation:

1. Pause and ask the user: "Root cause appears to be Y, not X. Should I update the task-plan docs?"
2. On approval, update the following:
   - **findings.md** — revise root cause analysis (primary target)
   - **tasks.md** — adjust implementation steps to match the new cause
   - **progress.md** — record why and when the direction changed
3. README.md describes symptoms/requirements only — do not update

## Implementation Rules

### Use Specialized Agents for Code Changes

When the user requests code changes (implementation, modification, bug fix, refactoring — any action that creates/updates/deletes code), **always use specialized agents.**

#### Agent Selection Criteria

| Work Type                                                                                             | Agent                                                               |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Type/interface definitions, API clients, utilities, services, state management setup, data transforms | `implement-engineering`                                             |
| Components, hooks, styling, screens, navigation, UI state handling                                    | `implement-react`                                                   |
| Mixed (data layer + UI)                                                                               | `implement-engineering` first → then `implement-react` sequentially |

### Session Handoff

When a new session starts in a project with ongoing work:

1. Read `progress.md` from `docs/plans/` subfolders where status is "진행중"
2. Check the last session's current state and report to the user
3. Continue after user approval

### PR Creation Rules

When creating a PR, reference all 5 files in the task folder:

- Include the Jira issue number in the PR title (from README.md)
- PR body: overview (README) / changes (tasks + changed files) / review focus (findings technical decisions)
