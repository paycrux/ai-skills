---
name: qa-guide
description: Generate a QA test guide in markdown from task-plan documents.
argument-hint: [task-folder-name or jira-issue]
---

# /qa-guide — QA Test Guide Generator

Reads the task-plan documents (`README.md`, `spec.md`, `tasks.md`, `progress.md`, `findings.md`) and produces a structured QA test guide in markdown that the QA team can use immediately.

## Argument Parsing

- `/qa-guide` — auto-detect the most recent in-progress or completed plan folder
- `/qa-guide <task-folder-name>` — use `docs/plans/<task-folder-name>/`
- `/qa-guide <jira-issue>` — find the folder whose `README.md` contains the issue number

## Source Discovery

1. If no argument is given, scan `docs/plans/` for a folder whose `README.md` status is "진행중" or "완료".
2. Once the folder is identified, read all five files:
   - `README.md` — background, goals, scope, issue number
   - `spec.md` — behavior flows, edge cases
   - `tasks.md` — completed feature checklist
   - `progress.md` — actual implementation details, changed files, notable findings
   - `findings.md` — technical decisions, platform differences

## Output

**Save path:** `docs/plans/<task-folder-name>/qa-guide.md`

Overwrite if the file already exists (always keep it up to date).

## Document Structure

Use the template below as the default.

```markdown
# QA 테스트 가이드 — {Feature Name}

> 이슈: {JIRA-ISSUE}
> 작성일: {today}

## 개발 개요

(구현된 기능 요약 — 2~4줄. README.md와 tasks.md 기준)

---

## 테스트 환경

### 테스트 기기
- (플랫폼별 기기 요건 — Android / iOS)

### 사전 준비
- (테스트 전 필요한 설정, 계정, 권한, 데이터 등)

---

## 테스트 시나리오

### {기능 그룹 1}

| # | 조건 | 액션 | 기대 결과 |
|---|------|------|-----------|
| 1-1 | | | |

### {기능 그룹 2}
...
```

## Scenario Writing Rules

1. **Include only must-test core features** — do not list every implementation detail.
2. **Happy Path only** — exclude edge cases and error scenarios.
3. **Select only key features** from completed items in `tasks.md`.
4. Expected results must be specific ("navigate to screen" ✗ → "navigate to the Return Failure screen" ✓).
5. Condition column: app state (foreground / background / terminated), device, preconditions.
6. Scenario numbers follow `{group}-{index}` format (e.g., 1-1, 2-3).
7. If platform differences exist, note Android/iOS in the Condition column.

## Language

- Write in **Korean** (QA team's working language)
- Keep technical terms as-is (포그라운드, 백그라운드, FCM, etc.)
- Keep table cells concise (1–2 lines per cell)

## Completion

Report the file path and a brief summary:

> `qa-guide.md` saved → `docs/plans/{folder}/qa-guide.md`
> {N} scenarios across {M} groups
