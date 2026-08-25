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
4. Ask the user to review. Apply requested changes, then follow **Open questions** below.
5. Suggest `/implement {name}`.

## Open questions

Anything the plan cannot decide on its own goes in a `## 확인 필요` section in `tasks.md` — one line per question, phrased so the answer is a choice, not an essay.

Once a question is answered, **delete the question line and keep only the decision.** Never leave the request and its answer side by side; a reader opening the doc later needs the conclusion, not the negotiation that produced it.

- The decision goes wherever it changes the work — the Phase task line, `spec.md`, or one line under `## 진행 기록` when it changes neither.
- Record the decision only, in one line. No restating the options, no "사용자 확인 완료" markers.
- When the last question is answered, delete the `## 확인 필요` section itself.

## Communication Style

Write for a reader who has not implemented this feature and does not share your context.

- Explain the background before the conclusion. A sentence that only makes sense to someone who already read the code is worth nothing to the reader.
- Never drop an internal term without unpacking it — serialization formats, protocol details, library internals, framework behavior. Either spend a sentence on what it is and why it matters here, or leave it out.
- When the background costs more than two or three sentences to explain, compress the whole point to one line instead. One clear line beats a paragraph the reader skips.
- No filler: 전반적으로, ~등을 개선, 안정성 향상 and the like add length without information.

This applies to conversational output in this flow and to free-text prose inside `tasks.md`/`spec.md`. Structured elements — headers, checklists, tables, file paths, figma links — keep their normal format.

## Notes

- Task type is a header field on `tasks.md`: `작업 종류: 버그 수정 | 기능 개발 | 기능 수정`. There is no type-branching elsewhere.
- For "기능 수정" referencing an existing feature, add a `참조:` header link to the original plans. Do not modify any file in the original `plans/`.
- Each Phase task line has a file path in backticks and an optional figma node link inline. If one node maps to multiple sub-areas, split into separate task lines.
- Output documents are written in Korean.
- Do not start `/implement` from this skill — only suggest it.
