---
name: task-plan
description: Workflow for creating a task folder, writing documentation, and implementing new features or bug fixes.
argument-hint: <task description or Jira issue number>
---

# Task Plan Workflow

Follow this workflow whenever a user requests a new task (feature development, bug fix, etc.).

## Phase 0: Documentation

### 1. Create Folder

Create `docs/plans/{task-name}/`.

- Folder name: kebab-case, no issue number in the name
- Record the issue number inside `README.md`

### 2. Determine Task Type

Classify the task to decide which sections to include:

```
Does the task involve UI/frontend work?
├── YES → mark as "frontend" (include UI sections in spec.md)
│   ├── UI only (presentational changes, styling)
│   ├── UI + business logic (state management, data flow, API integration)
│   └── Full-stack (backend + frontend)
└── NO → mark as "backend-only" (skip UI sections)
```

This classification determines:

- Whether to create `ui-spec.md` (frontend tasks only)
- Whether to include "state location decisions" section in `spec.md`
- Whether to search for reusable components in Step 3
- Whether to apply React implementation rules in Phase 1–N

### 3. Explore Codebase (findings)

Use the Explore sub-agent to scan the codebase.

**Scope decision flow:**

```
Did the user specify a scope?
├── YES → explore only that scope
└── NO
    ├── Does CLAUDE.md have a Project Structure section?
    │   ├── YES → explore using spec keywords + structure
    │   └── NO → ask the user to narrow the scope
    │
    └── Are there too many results?
        ├── YES → ask the user to narrow the scope
        └── NO → proceed

If the user says "brand new feature" or "not sure":
    → only identify project conventions/structure and suggest file locations
```

**Two-pass exploration:**

Pass 1 — keyword search: collect files directly related to keywords extracted from the spec
Pass 2 — structure tracing: trace the import/export chain one level from Pass 1 files + check app entry points

**findings.md recording principles:**

- Directly related files (keyword matches)
- Files in the blast radius (import/structure tracing)
- Confirmed unrelated files (only those that appeared in search but require no changes — skip obviously unrelated ones)

#### Frontend additional exploration (when task type includes frontend)

After the two-pass exploration, run a third pass for UI component reuse:

**Pass 3 — component reuse search:**

1. Extract UI elements needed from the spec/requirements (buttons, modals, forms, tables, etc.)
2. Search the existing codebase for matching components:
   - `Glob: src/**/components/**/*.tsx` for shared/common components
   - `Grep: "export.*function|export.*const"` in component directories
   - Check for design system / UI library usage (e.g., component library imports)
3. For each UI element needed, record in findings.md:
   - **Reuse**: existing component fits as-is → record path
   - **Extend**: existing component needs minor modification → record path + what to change
   - **New**: no suitable existing component → note why

Also identify:

- Design tokens / theme in use (spacing, colors, typography patterns)
- State management patterns used in the project (useState, zustand, redux, react-query, etc.)
- Routing conventions

**Pass 4 — library & pattern survey:**

For each feature area the task requires (form, table, data fetching, modal, etc.):

1. Check `package.json` for relevant libraries (react-hook-form, tanstack-query, zod, etc.)
2. Find existing implementations of the same feature in the codebase
   - e.g., if the task needs a form → search for existing form components, observe how validation/submit/error handling is done
3. Record in findings.md "Library & Existing Implementation Patterns" table:
   - Which library is used
   - Example file path
   - Pattern summary (how it's structured, naming conventions, error handling style)
4. **Implementation must follow these established patterns** — do not introduce a new library or pattern without explicit user approval

### 4. Analyze Reference Documents

If the user attaches a design doc, API spec, design document, or implementation guide:

**Reflect in README.md:**

- Extract background/purpose and populate the background and goals sections.

**Reflect in spec.md:**

- Extract feature flows and convert to pseudocode.
- If an API spec is present, list endpoints with request/response in the API integration section.
- If state definitions or edge cases are present, add them to the appropriate sections.

**Reflect in tasks.md:**

- If concrete implementation methods are included, add them to the Phase checklists.
- If code examples or library usage are present, summarize them in the relevant task.

**Reflect in findings.md:**

- Record existing code, file paths, and dependency information mentioned in the reference document.
- Add any technical decisions to the technical decisions section.

**Principle: distribute the key content of reference documents across the plan files so that future work does not require reopening the originals.**

#### Figma link handling

If the user provides a Figma link:

```
Is Figma MCP server available? (check tool list for figma/design tools)
├── YES → fetch design data via MCP
│   - Extract screen structure, component hierarchy, spacing, colors
│   - Record in ui-spec.md and findings.md
└── NO → notify user:
    "Figma MCP 서버가 연결되어 있지 않습니다.
     다음 중 하나를 제공해주세요:
     - 화면별 스크린샷
     - 디자인 스펙 (컴포넌트 구조, 간격, 색상 등)
     - 또는 Figma MCP 서버를 설정해주세요"
    → wait for user input before proceeding
```

#### Design reference availability (for UI quality)

```
Does the task have a design reference? (Figma, screenshots, design spec)
├── YES → follow the provided design faithfully
│   - Colors, spacing, typography, layout from the design source
│   - Record design source in ui-spec.md header
└── NO → apply `.claude/rules/frontend-design.md` during implementation
    - Prevents AI slop (generic fonts, cliché color schemes)
    - Forces context-appropriate, creative design choices
    - Mark in ui-spec.md: "디자인 레퍼런스 없음"
```

### 5. Write Documents

Write in this order:

1. `README.md` — overview, issue number, goals, scope
2. `spec.md` — pseudocode, behavior flows, state definitions (+ state location decisions if frontend task)
3. `ui-spec.md` — **(frontend tasks only)** screen structure, component breakdown, state×display matrix, reuse map
4. `findings.md` — two-pass exploration results (+ component reuse map if frontend task)
5. `tasks.md` — concrete implementation checklist based on spec + findings + ui-spec
6. `progress.md` — initialize (empty)

Write **all documents at once**, then run the template compliance check before asking for user review.

> Relationship between `spec.md` and `ui-spec.md`: the "state location decisions" section in spec.md determines the component breakdown in ui-spec.md. Write spec.md first, then use its state structure as the basis for ui-spec.md.

### 6. Template Compliance Check & Document Evaluation

After writing all documents, verify each file against its template before asking for user review.
If any check fails, rewrite that file immediately — do not proceed to the evaluation step.

**README.md**

- [ ] Contains `이슈:`, `생성일:`, `상태:` fields
- [ ] Has `배경`, `목표`, `범위` sections

**spec.md**

- [ ] Has `화면/기능 흐름`, `상태 정의`, `엣지 케이스` sections
- [ ] (frontend) Has `상태 위치 결정` section with at least one table row

**findings.md**

- [ ] Has `직접 관련` and `영향 범위` sections
- [ ] `직접 관련` has at least one file entry

**tasks.md**

- [ ] Has at least one `## Phase N:` header
- [ ] Every checklist item includes a file path in backticks

**ui-spec.md** (frontend tasks only)

- [ ] Has `화면 구조`, `컴포넌트 분해`, `상태 × 표시 매트릭스`, `컴포넌트 재사용 맵` sections
- [ ] Component breakdown table has at least one row

### 7. Document Quality Evaluation

After passing the template compliance check, run the `evaluate-docs` agent to pre-verify document quality before user review.

1. Run the `evaluate-docs` agent (pass the task folder path)
2. If evaluation result is **grade B or above** → proceed to Step 8 (user review)
3. If evaluation result is **grade C or below** → fix cited CRITICAL/MAJOR items and re-evaluate (max 2 times)
4. If still C or below after 2 re-evaluations → proceed to user review as-is, sharing the evaluation results

### 8. Review

Ask the user to review all documents:

- "문서 작성을 완료했습니다. 검토 후 수정할 내용이 있으면 알려주세요."
- If the user requests changes, apply them and confirm again.
- Record changes in `progress.md`.

## Phase 1–N: Implementation

Start implementation once the user approves.

### Rules During Implementation

- Follow the `tasks.md` checklist in order.
- Add technical facts discovered during implementation to `findings.md`.
- **After each phase**, record in `progress.md`:
  - Work done
  - Modified files
  - Current status (completed items, next task, blockers)
- Update `tasks.md` checklist (`- [ ]` → `- [x]`).

#### React/TypeScript Rules (when task type includes frontend)

Read `.claude/rules/react-typescript.md` before starting implementation and follow it throughout.
This rules file is maintained separately and referenced by other workflows (e.g., implement skill) as well.

### When Direction Changes

If the user requests a direction change:

1. Record the change in `progress.md` (before → after → reason).
2. Update `spec.md`.
3. Update `tasks.md`.
4. Do not update `README.md` unless the goal itself changed.

## Session Handoff

When resuming work in a new session:

1. Read `progress.md` to confirm the last state.
2. Check `tasks.md` for remaining work.
3. Restore technical context from `findings.md`.
4. Report current status to the user, then continue.

## Task Completion

When all phases are done:

1. Verify all items in `tasks.md` are checked.
2. Write the final session entry in `progress.md`.
3. **Auto-run `/evaluate`** — execute the evaluate skill with the task folder path (e.g. `/evaluate docs/plans/<task-name>/`).
   - The evaluate report will be saved as `docs/plans/<task-name>/evaluate.md` (handled by the evaluate skill's Step 5).
   - If CRITICAL/MAJOR violations are found, follow the evaluate skill's user review flow (fix or skip).
   - Once the evaluation is resolved (fixes applied or user chose to keep as-is), proceed to the next step.
4. Change the `README.md` status to "완료".

## Creating a PR

When the user requests a PR:

- Reference all plan files (5 files; 6 if frontend task, including ui-spec.md).
- Include the issue number in the PR title.
- PR body: overview (README) / changes (tasks + changed files) / review focus (findings technical decisions)

## Templates

See the `templates/` directory for each file's template.
