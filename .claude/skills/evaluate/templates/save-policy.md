# Evaluation Report Save Policy

## Output Path

| Condition | Output path |
|---|---|
| A specific folder path was provided as argument (e.g. `/evaluate docs/plans/my-task/`) | `<given-path>/evaluate.md` |
| A task-plan folder name was provided (e.g. `/evaluate my-task`) | `docs/plans/<my-task>/evaluate.md` |
| No path given (e.g. bare `/evaluate`) | `docs/evaluate/evaluate.md` (create `docs/evaluate/` if it does not exist) |

## Write Strategy

```
Does evaluate.md already exist at the target path?
├── YES → append a new evaluation entry to the existing file
│   - Add a horizontal rule (---) separator
│   - Add a timestamp header: `## 재평가 — {YYYY-MM-DD HH:mm}`
│   - Append the full report below the header
│   - Previous evaluation entries remain intact for history
└── NO → create evaluate.md with the full report
```

## Rules

- Do **not** create timestamped files like `evaluate-<date>.md`. A single `evaluate.md` file accumulates all evaluation history for one task.
- Write the full report into the markdown file. Do not truncate or summarize — the file must contain the complete report.
- When the target directory does not exist, create it before writing.
- Always use a single `evaluate.md` per target — append to it, never create separate files.
- After saving, print the file path so the user knows where the report was written.
