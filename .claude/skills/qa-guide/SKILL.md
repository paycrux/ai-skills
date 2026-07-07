---
name: qa-guide
description: Generate a QA test guide in markdown from task-plan documents.
argument-hint: [task-folder-name or jira-issue]
---

# /qa-guide — QA Test Guide Generator

Reads the task-plan documents (`tasks.md`, `spec.md`) and produces a structured QA test guide in markdown that the QA team can use for manual testing.

## Argument Parsing

- `/qa-guide` — auto-detect the most recent in-progress or completed plan folder
- `/qa-guide <task-folder-name>` — use `docs/<task-folder-name>/plans/`
- `/qa-guide <jira-issue>` — find the folder whose `tasks.md` header `이슈:` field contains the issue number

## Source Discovery

1. If no argument is given, grep `docs/*/plans/tasks.md` for header field `상태: 진행중` or `상태: 완료`. If multiple folders match, ask the user to choose.
2. Once the folder is identified, read both files under `docs/<task-folder-name>/plans/`:
   - `tasks.md` — header (issue, task type, status), overview, per-phase checklist, `## 진행 기록`
   - `spec.md` — feature flows, state definitions, edge cases

## Output

**Save path:** `docs/<task-folder-name>/qa-guide.md`

Overwrite if the file already exists (always keep it up to date).

## Document Structure

Use the template below as the default.

```markdown
# QA 테스트 가이드 — {Feature Name}

> 이슈: {JIRA-ISSUE}
> 작성일: {today}

## 개발 개요

(구현된 기능 요약 — 2~4줄. tasks.md 헤더/개요 기준)

---

## 테스트 환경

### 사전 조건

- (로그인 요구사항, 필요 권한, 기기/브라우저 요건)

### 테스트 데이터

- (필요한 구체적 데이터: 계정, 상품, 설정 등)

---

## 테스트 시나리오

### {기능 그룹 1}

| #   | 조건 | 액션 | 기대 결과 |
| --- | ---- | ---- | --------- |
| 1-1 |      |      |           |

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
8. **When a feature has 2+ toggles/states/options worth checking together** (e.g. logged-in/logged-out × free/premium), add one extra row per combination directly in the same scenario table instead of a separate matrix — make the Condition column specific about which combination is under test.

## Language

- Write in **Korean** (QA team's working language)
- Keep technical terms as-is (포그라운드, 백그라운드, FCM, etc.)
- Keep table cells concise (1–2 lines per cell)

## Communication Style

Apply the `caveman` skill to both:
- Conversational output in this flow (completion report)
- Free-text prose inside `qa-guide.md` (개발 개요, 사전 조건/테스트 데이터 bullets)

Keep structured elements — the scenario table, headers — in their normal format. Do not caveman-ify those.

## Completion

Report the file path and a brief summary:

> `qa-guide.md` saved → `docs/{folder}/qa-guide.md`
> {N} scenarios across {M} groups
