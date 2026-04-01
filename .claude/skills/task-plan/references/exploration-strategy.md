# Codebase Exploration Strategy

## Scope Decision

```
Did the user specify a scope?
├── YES → explore only that scope
└── NO
    ├── CLAUDE.md has Project Structure? → use spec keywords + structure
    ├── Too many results? → ask user to narrow scope
    └── User says "brand new" / "not sure" → identify conventions only, suggest file locations
```

## Two-Pass Exploration (All Tasks)

**Pass 1 — Keyword Search:**
Collect files directly related to keywords extracted from the spec.

**Pass 2 — Structure Tracing:**
Trace import/export chain one level from Pass 1 files + check app entry points.

**findings.md recording:**

| Category | What to record |
|---|---|
| 직접 관련 | Keyword-matched files |
| 영향 범위 | Import/structure-traced files |
| 관련 없음 확인 | Files that appeared in search but need no changes (skip obviously unrelated) |

## Frontend Additional Passes (When Task Includes UI)

**Pass 3 — Component Reuse Search:**

1. Extract UI elements needed from spec (buttons, modals, forms, tables, etc.)
2. Search existing codebase:
   - `Glob: src/**/components/**/*.tsx` for shared components
   - `Grep: "export.*function|export.*const"` in component directories
   - Check for design system / UI library usage
3. For each UI element, record in findings.md:
   - **재사용**: existing component fits as-is → record path
   - **확장**: needs minor modification → record path + what to change
   - **신규**: no suitable component → note why

Also identify:
- Design tokens / theme in use
- State management patterns (useState, zustand, redux, react-query, etc.)
- Routing conventions

**Pass 4 — Library & Pattern Survey:**

For each feature area the task requires (form, table, data fetching, modal, etc.):

1. Check `package.json` for relevant libraries
2. Find existing implementations of the same feature
3. Record in findings.md "라이브러리 & 기존 구현 패턴" table:
   - Which library is used
   - Example file path
   - Pattern summary
4. **Follow established patterns** — do not introduce new libraries without user approval
