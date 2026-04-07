---
name: finalize
description: "Finalize task documents after implementation, evaluation, and QA are complete. Merges Implementation Map into spec.md, deletes temporary documents. Use when user runs /finalize after all work on a task is done."
argument-hint: "<task-folder-name>"
disable-model-invocation: true
allowed-tools: Read, Edit, Glob, Bash
---

# /finalize — Task Document Finalization

Consolidate task documents into a minimal, long-lived set. Merges implementation details into spec.md and removes temporary working documents.

## Argument Parsing

- `/finalize <task-folder-name>` — resolves to `docs/<task-folder-name>/plans/`
- `/finalize <path>` — direct path to task folder
- `/finalize` — auto-detect: find task folders with README.md status "완료" under `docs/`; if multiple found, ask user to choose

## Precondition Check

Read `spec.md` in the task folder. If not found → error:

```
Error: spec.md not found in <path>.
/finalize requires documents created through the task-plan workflow.
```

## Step 1: Read Available Documents

Read all existing documents in parallel (skip any that don't exist):

| File | Purpose for finalize |
|---|---|
| `spec.md` | Target for Implementation Map merge |
| `tasks.md` | Source: phase checklists with file paths |
| `findings.md` | Source: technical decisions |
| `progress.md` | Source: modified file lists per phase |
| `evaluate.md` | Source: key decisions from violation fixes |
| `ui-spec.md` | Check existence only (preserved) |
| `test-cases.md` | Check existence only (preserved) |

## Step 2: Build Implementation Map

Extract implementation details from the documents read in Step 1:

```
tasks.md phases → which files implement which features
findings.md "기술 결정" table → why each approach was chosen
progress.md modified files → verify completeness
evaluate.md fix decisions → approach changes worth recording
```

Compose the map:

```markdown
## Implementation Map

| Spec Item | Files | Key Decisions |
|---|---|---|
| {spec.md flow/section name} | {comma-separated file paths, relative to project root} | {why this approach — from findings.md or evaluate.md} |
```

Rules:
- Group rows by spec.md section names (화면/기능 흐름, 상태 정의, etc.)
- Every file path from tasks.md must appear in at least one row
- Key Decisions: prefer findings.md "기술 결정" entries; add evaluate.md decisions only if they changed the implementation approach
- If a source document is missing, build the map from whatever is available

## Step 3: Merge into spec.md

1. Append `## Implementation Map` section at the end of spec.md
2. If evaluate.md contains decisions that affect behavioral spec (not just code quality), merge them into the relevant spec.md sections
3. Do not duplicate — if a decision already exists in spec.md, skip it

## Step 4: Update README.md

Set status to "완료" if not already.

## Step 5: Delete Temporary Documents

Delete from the task folder:

| Delete | Reason |
|---|---|
| `findings.md` | Merged into spec.md Implementation Map |
| `tasks.md` | Checklist — no value after completion |
| `progress.md` | Session log — git history is authoritative |
| `evaluate.md` | Key decisions merged into spec.md |
| `qa-report.md` | One-time verification result |
| `qa-guide.md` | One-time QA team guide |

Preserve:

| Keep | Reason |
|---|---|
| `README.md` | Task entry point — overview, background, goals |
| `spec.md` | Behavioral spec + Implementation Map |
| `ui-spec.md` | Component structure (frontend only) |
| `test-cases.md` | Reusable for regression testing |

## Step 6: Report

```
Finalization complete: <task-folder-name>

Preserved:
  - README.md
  - spec.md (Implementation Map added)
  - ui-spec.md (if existed)
  - test-cases.md (if existed)

Deleted: <list of actually deleted files>
```

## Edge Cases

| Condition | Action |
|---|---|
| Already finalized (no temporary docs) | Report "Already finalized, no changes needed" |
| No evaluate.md | Skip evaluate merge, build map from other sources |
| No tasks.md but other temp docs exist | Build map from findings.md + progress.md |
| No temporary docs at all, but spec.md has no Implementation Map | Ask user: "No source documents found. Provide file paths manually or skip?" |

## Rules

- **spec.md must exist** — error if missing
- **Never modify ui-spec.md or test-cases.md** — only check existence
- **Delete only the documented temporary files** — never delete unknown files
- Communicate with the user in Korean
