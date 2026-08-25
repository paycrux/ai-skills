---
name: qa-guide
description: Write a QA test guide as a section inside task-plan's tasks.md, optionally syncing it to the Jira issue description.
argument-hint: [task-folder-name or jira-issue]
---

# /qa-guide — QA Test Guide Generator

Reads the task-plan documents (`tasks.md`, `spec.md`) and writes a QA test guide as a `## QA 가이드` section directly inside `tasks.md`. This is not a separate document — task-plan's `tasks.md` stays the single source of truth, and the QA team reads the guide from the same file.

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

**Target file:** `docs/<task-folder-name>/plans/tasks.md` — write the guide as a `## QA 가이드` section inside this file. Do not create a separate `qa-guide.md` file.

- If a `## QA 가이드` section already exists, replace it in place (always keep it up to date).
- If it doesn't exist yet, insert it right before the `## 진행 기록` section. If `tasks.md` has no `## 진행 기록` section, append it at the end of the file.

## Document Structure

Use the template below as the default for the section content.

```markdown
## QA 가이드

### 테스트 환경

#### 사전 조건

- (로그인 요구사항, 필요 권한, 기기/브라우저 요건)

#### 테스트 데이터

- (필요한 구체적 데이터: 계정, 상품, 설정 등)

### 테스트 시나리오

#### {기능 그룹 1}

| #   | 조건 | 액션 | 기대 결과 |
| --- | ---- | ---- | --------- |
| 1-1 |      |      |           |

#### {기능 그룹 2}

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

Write for a reader who has not implemented this feature and does not share your context.

- Explain the background before the conclusion. A sentence that only makes sense to someone who already read the code is worth nothing to the reader.
- Never drop an internal term without unpacking it. Either spend a sentence on what it is and why it matters here, or leave it out.
- When the background costs more than two or three sentences to explain, compress the whole point to one line instead.
- No filler: 전반적으로, ~등을 개선, 안정성 향상 and the like add length without information.

This applies to conversational output in this flow (completion report) and to free-text prose inside the `## QA 가이드` section (사전 조건/테스트 데이터 bullets). The scenario table and headers keep their normal format.

QA readers did not write the code. A step they cannot follow without asking the implementer is a broken step.

## Jira Sync

The `## QA 가이드` section in `tasks.md` is written unconditionally as the primary output. After that, check the `tasks.md` header for an `이슈:` field — if it contains a Jira issue key, additionally try to mirror just that section into the issue's description so the QA team sees it in Jira too. If there is no issue key, skip this section entirely — do not run any `acli` command.

### Readiness check

Run `acli jira auth status`.

- If the command is not found (acli not installed), or it reports the user is not logged in, **do not install or log in automatically**. Skip the Jira sync and show the recommendation block below instead — the `## QA 가이드` section is already in `tasks.md`, so nothing is lost.
- Only proceed to the update steps below if acli is installed and authenticated.

### Update steps (acli ready)

1. **Convert the `## QA 가이드` section to ADF** — convert just that section's markdown to Atlassian Document Format (ADF) JSON: headings, paragraphs, lists, code spans, horizontal rules, and tables become ordinary ADF nodes. Do not use `taskList`/`taskItem` nodes; represent any checklist-style line as a bullet list item whose text starts with `[ ]`.
2. **Update the issue** — `acli jira workitem edit --key "<ISSUE-KEY>" --description-file "<adf-file>" --yes`
3. **Verify** — `acli jira workitem view <ISSUE-KEY> --fields description --json` and confirm the description contains `0` `taskItem` nodes and the expected heading/list/table structure.

### When acli isn't ready

Don't ask to install it — just surface a recommendation:

> Jira 자동 업데이트는 스킵했어 (acli 미설치 또는 로그인 안 됨). QA 섹션은 이미 tasks.md에 반영했으니 내용은 안 빠졌어.
> 다음에 자동 동기화하려면:
> 1. 설치 — macOS: `brew install acli` (다른 OS는 Atlassian 공식 문서 참고)
> 2. 로그인 — `acli jira auth login`
> 준비되면 `/qa-guide`를 다시 실행하면 Jira 이슈 설명까지 자동으로 업데이트돼.

## Completion

Report the target file, a brief summary, and the Jira sync outcome:

> `tasks.md`에 QA 가이드 반영 완료 → `docs/{folder}/plans/tasks.md`
> {N} scenarios across {M} groups
> Jira {ISSUE-KEY} 이슈 설명 업데이트 완료 ✅ (or: 스킵 — 이슈 없음 / acli 미설치·미로그인 → 설치·로그인 권장 안내 표시)
