---
name: task-plan
description: "Lightweight task planning. Writes tasks.md + spec.md under docs/{name}/plans/ from a description. Use when the user runs /task-plan or wants structured planning before implementation."
argument-hint: <task description or Jira issue number>
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# /task-plan

Write `docs/{task-name}/plans/tasks.md` + `spec.md` from the user input, then hand off.

## Flow

1. Parse input — extract kebab-case task name and issue number if present.
2. If the input lacks codebase context, grep for keywords and check related files. Inline findings (reusable components, library patterns, related files) as sub-bullets under the Phase task that will use them.
3. Write the two docs using the templates in `${CLAUDE_SKILL_DIR}/templates/`.
4. Ask the user to review. Apply requested changes and record them in `tasks.md` under `## 진행 기록`.
5. Suggest `/implement {name}`.

## Notes

- Task type is a header field on `tasks.md`: `작업 종류: 버그 수정 | 기능 개발 | 기능 수정`. There is no type-branching elsewhere.
- For "기능 수정" referencing an existing feature, add a `참조:` header link to the original plans. Do not modify any file in the original `plans/`.
- Each Phase task line has a file path in backticks and an optional figma node link inline. If one node maps to multiple sub-areas, split into separate task lines.
- Output documents are written in Korean.
- Do not start `/implement` from this skill — only suggest it.
