---
name: test-case
description: Generate manual/automated test cases from implemented code, task-plan documents, or user descriptions. Covers happy paths with combinatorial state coverage. Output is human-readable and machine-parseable for agent-browser and e2e test generation.
argument-hint: [task-folder-name, file-path, or feature description]
---

# /test-case — Test Case Generator

Generates structured test cases from implemented code, task-plan documents, or user descriptions.
Output is formatted for three audiences: humans doing manual testing, agent-browser for automated execution, and e2e test code generation (Playwright/Cypress).

## Argument Parsing

- `/test-case` — auto-detect the most recent in-progress or completed plan folder in `docs/`
- `/test-case <task-folder-name>` — use `docs/<task-folder-name>/`
- `/test-case <file-path>` — analyze the specified file (component, page, etc.) directly
- `/test-case <feature description>` — generate based on the user's feature description

Parse `$ARGUMENTS`:

- If a matching folder exists in `docs/` → task-plan based
- If it looks like a file path (`/`, `./`, `../`, `~`, or contains file extensions) → direct file analysis
- Otherwise → treat as feature description

## Source Discovery

### When task-plan based

Read the following files:

- `README.md` — background, goals, scope
- `spec.md` — behavior flows, state definitions
- `ui-spec.md` — (if exists) screen structure, components, state×display matrix
- `tasks.md` — completed feature checklist
- `progress.md` — actual implementation details, changed files

### When file based

1. Read the file and analyze component/page structure
2. Trace the import chain one level to identify related files
3. Check routing configuration for the page's URL path

### When description based

Extract from the user's description:

- Screens/pages involved
- User actions (click, input, navigation)
- State transitions (loading, success, error, etc.)
- Conditional branches (permissions, data presence, etc.)

## Test Case Writing Rules

### 1. Happy Path Only

- Write only normal operation scenarios
- Exclude error cases and edge cases
- Focus on "the user successfully uses the feature from start to finish"

### 2. Combinatorial Coverage

When there are multiple states or options, write a **combination matrix** instead of a single case.

**Identify combination targets:**

- 2+ buttons (e.g., Save/Cancel, Approve/Reject)
- 2+ states (e.g., logged-in/logged-out, data exists/empty)
- 2+ options (e.g., free tier/premium, domestic/international)
- Toggles/checkboxes on/off

**Combination matrix format:**

```markdown
#### Combination Matrix: {Feature Name}

| Condition A | Condition B | Expected Result |
| ----------- | ----------- | --------------- |
| State 1     | State 1     | Result          |
| State 1     | State 2     | Result          |
| State 2     | State 1     | Result          |
| State 2     | State 2     | Result          |
```

When there are 3+ conditions, use pairwise combinations instead of exhaustive (2-way covering).

### 3. Dual Format: Human + Machine

Each test case must serve two audiences:

- **Humans**: natural language steps that can be followed manually
- **agent-browser / e2e**: structured data that can be parsed for automation

To achieve this, include a **selector hint** in each step.

## Output

**Save path:** depends on source

- Task-plan based: `docs/<task-folder-name>/test-cases.md`
- File/description based: `test-cases-{feature-slug}.md` in the current directory

## Template

Read `templates/test-cases.template.md` and use it as the base structure.

### Template usage rules

1. **Follow the template structure** — all sections in the template must appear in the output in the same order.
2. **Do not remove template sections** — if a section is not applicable, write "N/A" with a brief reason instead of deleting it.
3. **Additions are allowed within sections** — if the feature warrants extra sub-sections, columns, or verification points beyond what the template shows, add them inside the relevant section.
4. **Propose improvements, don't silently deviate** — if you believe an additional section or structural change would significantly improve the test cases (e.g., a "Data Setup Script" section, a "Visual Regression" checklist), propose it to the user before adding. Frame it as: "The template covers X, but for this feature I'd also suggest adding Y because Z. Should I include it?"
5. **Template comments are instructions** — HTML comments (`<!-- ... -->`) in the template are writing guidance, not content to copy into the output.

## Step Writing Rules

### Standardized Action Verbs

Use only these verbs to enable agent-browser parsing and e2e conversion:

| Verb       | Meaning                                 | e2e Mapping                              |
| ---------- | --------------------------------------- | ---------------------------------------- |
| `navigate` | Go to a URL                             | `page.goto()`                            |
| `click`    | Click an element                        | `page.click()`                           |
| `type`     | Enter text                              | `page.fill()`                            |
| `select`   | Choose from dropdown                    | `page.selectOption()`                    |
| `toggle`   | Switch checkbox/toggle                  | `page.check()` / `page.uncheck()`        |
| `scroll`   | Scroll the page                         | `page.evaluate(() => window.scrollTo())` |
| `wait`     | Wait for element/state                  | `page.waitForSelector()`                 |
| `verify`   | Assert (not an action, validation only) | `expect()`                               |
| `hover`    | Mouse over                              | `page.hover()`                           |
| `drag`     | Drag and drop                           | `page.dragAndDrop()`                     |
| `upload`   | Upload a file                           | `page.setInputFiles()`                   |

### Selector Hint Priority

1. `data-testid="xxx"` — use as-is if present in code
2. `role="button" name="Save"` — accessibility attributes
3. `text="Save Changes"` — visible text
4. `.class-name` or `#id` — CSS selector
5. `{Save button}` — natural language description in curly braces (when no selector info is available)

When code is readable, use actual selectors as much as possible.
When code is unavailable or description-based, use natural language hints in `{curly braces}`.

### Expected Result Writing

- Be specific: "navigates away" ✗ → "navigates to order completion page (`/order/complete`)" ✓
- Focus on visible changes: "state changes" ✗ → "'Payment Complete' badge is displayed" ✓
- Include numbers when applicable: "list updates" ✗ → "item is removed from the list, total count shows N-1" ✓

## Combination Matrix Rules

1. List all conditions that are combination targets
2. Enumerate all possible values for each condition
3. For 2 conditions: exhaustive combinations (2×2=4, 2×3=6, etc.)
4. For 3+ conditions: pairwise combinations
5. Write specific expected results for each combination
6. Link each combination to its covering TC number in the `Related TC` column
7. If a combination is not covered by any existing TC, create an additional TC for it

## Language

- Write test case documents in **the user's working language** (match the language used in the source documents or conversation)
- Technical terms remain as-is (selector, click, navigate, data-testid, etc.)
- Automation metadata (YAML) is always in English

## Task-plan 연동

테스트 케이스 작성 완료 후, 관련 task-plan 폴더(`docs/*/`)가 존재하면 `progress.md`에 결과 요약을 append한다:

```markdown
### /test-case 결과 — {YYYY-MM-DD}
- 테스트 케이스: {N}건, 조합 매트릭스: {M}건
- 파일: `{test-cases.md 경로}`
```

## Completion

Report after writing:

> `test-cases.md` saved → `{file-path}`
> {N} test cases / {M} combination matrices
>
> Usage:
>
> - Manual testing: follow the step tables
> - agent-browser: `/agent-browser run TC-1 through TC-N from test-cases.md`
> - e2e conversion: generate Playwright/Cypress code from automation metadata + step tables
