# Test Cases — {Feature Name}

> Source: {task-plan folder | file path | "user description"}
> Created: {today}
> Target URL: {base-url}{path} (if known)

---

## Test Environment

### Prerequisites
<!-- List login requirements, necessary permissions, device/browser requirements -->
-

### Test Data
<!-- Specific data needed: accounts, products, settings, etc. -->
-

---

## TC-{N}: {Test Case Title}

> Purpose: {what this test verifies — 1 line}

### Initial State
<!-- Required app/page state before starting this test -->
-

### Steps

| # | Done | Action | Target | Expected Result |
|---|------|--------|--------|-----------------|
| 1 | [ ]  | {verb} | `{selector-hint}` {description} | {specific result} |

<!--
Action verbs (use only these):
  navigate, click, type, select, toggle, scroll,
  wait, verify, hover, drag, upload

Selector hint priority:
  1. data-testid="xxx"
  2. role="button" name="Save"
  3. text="Save Changes"
  4. .class-name or #id
  5. {natural language in curly braces}
-->

### Verification Points
<!-- Checkable assertions after completing all steps -->
- [ ] {checkpoint}

---

## Combination Matrices

### CM-{N}: {Feature Name} — {Condition Group}

<!--
Rules:
  - 2 conditions → exhaustive (2×2, 2×3, etc.)
  - 3+ conditions → pairwise combinations
  - Every row must link to a TC that covers it
  - If no TC covers a row, create one
-->

| Condition A | Condition B | Expected Result | Related TC |
|-------------|-------------|-----------------|------------|
| | | | TC-{N} |

---

## Automation Metadata

```yaml
feature: {feature-name}
base_url: {base-url or "TBD"}
auth_required: {true/false}
test_data:
  - type: {data type}
    description: {description}
selectors:
  - name: {element name}
    hint: {CSS selector or data-testid or role description}
    type: {button | input | link | text | checkbox | select}
```
