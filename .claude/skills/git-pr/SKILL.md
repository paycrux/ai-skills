---
name: git-pr
description: "Full Git PR workflow: choose git-only, PR-only, or both. Branch modes: create fresh branch from base, or commit/push current branch with optional suffix sub-branch and rebase. Handles staged and unstaged changes. Use /git-pr [--mode git|pr|both] [--new <name>] [--suffix <dev|stg>] [--base <branch>] [--no-rebase] [--also-pr <branch>] [--preview]"
argument-hint: "[--mode git|pr|both] [--new <name>] [--suffix <dev|stg>] [--base <branch>] [--no-rebase] [--also-pr <branch>] [--preview]"
disable-model-invocation: true
allowed-tools: Bash, AskUserQuestion, Read, Write, Edit
---

# /git-pr — Git PR Workflow

> All strings quoted in `AskUserQuestion` prompts and options are the literal Korean text shown to the user. Emit them verbatim.

## Step 1: Choose the operation

If `--mode` is not in `$ARGUMENTS`, call `AskUserQuestion` with:
- prompt: `"어떤 작업을 진행할까요?"`
- options: `["git — 브랜치 작업만 (PR 생성 없음)", "pr — PR만 생성 (현재 브랜치 기준)", "both — 브랜치 작업 + PR 생성"]`

If `--mode git|pr|both` is provided, skip Step 1.

---

## Step 2: Branch strategy (skip if mode is `pr`)

Call `AskUserQuestion` with:
- prompt: `"브랜치를 어떻게 할까요?"`
- options: `["새 브랜치 생성 — base 브랜치(develop/master(or main)/staging)에서 새로 분기", "현재 브랜치 사용 — 커밋·푸시 후 선택적으로 서브 브랜치 생성 및 리베이스"]`

If `--new <name>` is in `$ARGUMENTS` → New branch mode, skip Step 2.
If `--suffix` or no branch flags → Current branch mode, skip Step 2.

---

## Step 3: Handle working tree changes (skip if mode is `pr`)

Run:

```bash
git diff --quiet && git diff --cached --quiet && echo "clean" || echo "dirty"
```

```bash
git diff --cached --quiet && echo "no_staged" || echo "has_staged"
```

```bash
git diff --quiet && echo "no_unstaged" || echo "has_unstaged"
```

### Case A: both staged and unstaged changes

Call `AskUserQuestion` with:
- prompt: `"스테이징된 변경사항과 스테이징 안 된 변경사항이 모두 있어요. 어떻게 처리할까요?"`
- options: `["전체 스테이징 후 커밋 — git add -A 후 커밋", "스테이징된 것만 커밋 — 스테이징 안 된 변경사항은 그대로 유지", "전체 스태시 — git stash로 임시 보관 후 브랜치 작업 완료 뒤 복원"]`

### Case B: staged only

Ask for a commit message in plain conversation (in Korean), then commit:

```bash
git commit -m "<message>"
```

### Case C: unstaged only

Call `AskUserQuestion` with:
- prompt: `"스테이징 안 된 변경사항이 있어요. 어떻게 처리할까요?"`
- options: `["전체 스테이징 후 커밋 — git add -A 후 커밋", "스태시 — git stash로 임시 보관 후 브랜치 작업 완료 뒤 복원", "그냥 진행 — 변경사항 유지한 채로 진행 (현재 브랜치 모드에서만 가능)"]`

> In New branch mode, `그냥 진행` is not selectable — switching branches requires a clean tree or a stash.

### Case D: clean

No changes; continue.

---

## Mode A — Create a new branch

### A1: Collect options

If not provided via flags:
- Ask for the branch name in plain conversation, in Korean: `"새 브랜치 이름을 입력해주세요"`
- Call `AskUserQuestion` with:
  - prompt: `"어느 브랜치에서 분기할까요?"`
  - options: `["develop", "master (or main)", "staging"]`

> If `master (or main)` is selected, resolve the real branch name via **Base branch resolution** below.

### A2: Execute

```bash
git fetch origin {BASE}
git checkout -b {NEW_BRANCH} origin/{BASE}
git push -u origin {NEW_BRANCH}
```

If a stash was used in Step 3: `git stash pop`

Set `HEAD_BRANCH = {NEW_BRANCH}`.

If mode is `git` → [Report], done.
If mode is `both` → [PR Phase].

---

## Mode B — Use the current branch

### B1: Collect options

If not provided via flags:
- Call `AskUserQuestion` with:
  - prompt: `"서브 브랜치 suffix를 붙일까요? (예: feat/my-feature-dev)"`
  - options: `["dev — -dev 붙여서 서브 브랜치 생성", "stg — -stg 붙여서 서브 브랜치 생성", "없음 — 서브 브랜치 생성 안 함"]`
- Call `AskUserQuestion` with:
  - prompt: `"어느 브랜치 기준으로 리베이스할까요?"`
  - options: `["develop", "master (or main)", "staging", "리베이스 안 함"]`

> If `master (or main)` is selected, resolve the real branch name via **Base branch resolution** below.

### B2: Identify the current branch

```bash
git branch --show-current
```

Save as `ORIGIN_BRANCH`.
If a suffix is set: `SUB_BRANCH = {ORIGIN_BRANCH}-{suffix}`.

### B3: Push the origin branch

```bash
git push origin {ORIGIN_BRANCH}
```

### B4: Create the sub-branch (only when a suffix is set)

```bash
git branch -D {SUB_BRANCH} 2>/dev/null || true
git checkout -b {SUB_BRANCH}
```

> Never delete or modify the remote sub-branch.

### B5: Rebase (skip if `없음` or `--no-rebase`)

```bash
git fetch origin {BASE}
git rebase origin/{BASE}
```

On conflict:

1. List the conflicting files:
   ```bash
   git diff --name-only --diff-filter=U
   ```

2. Read each conflicting file and analyze both sides — `<<<<<<< HEAD` (this branch) and the part after `=======` (base branch):
   - Determine the **intent** of each side: new feature, bug fix, or refactor
   - Decide whether both sides must be kept (both-side merge) or one side wins
   - Explain the reasoning and the proposed resolution in Korean

3. Present the proposal via `AskUserQuestion` and get approval:
   - prompt: `"[파일명] 충돌 해결 제안입니다. [판단 근거 + 제안 내용]. 이대로 진행할까요?"`
   - options: `["이대로 진행", "직접 수정할게요 — 잠시 후 계속 진행해주세요"]`

4. On approval, use Edit to remove the conflict markers and apply the resolution. If the user chooses to fix it themselves, wait until they say they are done.

5. After resolving:
   ```bash
   git add {resolved_files}
   git rebase --continue
   ```

6. Repeat 2–5 for further conflicts until the rebase completes.

### B6: Push

```bash
git push --force-with-lease origin {SUB_BRANCH or ORIGIN_BRANCH}
```

### B7: Return to the origin branch (only when a suffix is set)

```bash
git checkout {ORIGIN_BRANCH}
```

If a stash was used in Step 3: `git stash pop`

`HEAD_BRANCH` = `{SUB_BRANCH}` if a suffix is set, else `{ORIGIN_BRANCH}`.

If mode is `git` → [Report], done.
If mode is `both` → [PR Phase].

---

## PR Phase (mode `pr` or `both`)

If mode is `pr` (no branch work was done):

```bash
git branch --show-current
```

Set `HEAD_BRANCH` = current branch.

### Collect PR options

Call `AskUserQuestion` with:
- prompt: `"PR의 대상 브랜치(base)를 선택해주세요."`
- options: `["develop", "master (or main)", "staging"]`

> If `master (or main)` is selected, resolve the real branch name via **Base branch resolution** below.

Call `AskUserQuestion` with:
- prompt: `"추가로 다른 브랜치에도 PR을 생성할까요? (예: develop → staging 동시 PR)"`
- options: `["없음 — PR 하나만 생성", "직접 입력 — 대상 브랜치를 입력해서 추가 PR 생성"]`

```bash
gh auth status
```

If not authenticated: tell the user in Korean to run `gh auth login`, then stop.

### Draft the PR

Analyze the branch changes:

```bash
git log origin/{PR_BASE}..{HEAD_BRANCH} --oneline
```

```bash
git diff origin/{PR_BASE}..{HEAD_BRANCH} --stat
```

```bash
git diff origin/{PR_BASE}..{HEAD_BRANCH} --name-status
```

Read the actual diff of the most substantial files before writing. Grouping requires knowing what the code does, not just which files changed.

Generate:

1. **PR title** — one line, what this PR does (Korean allowed)
2. **PR body** — apply the authoring rules below to `${CLAUDE_SKILL_DIR}/templates/pr-body.template.md`

Read `${CLAUDE_SKILL_DIR}/templates/pr-body.example.md` to calibrate sentence tone and density. It is a writing sample, not content to copy.

---

#### Authoring rules

**Core principle: every line must be verifiable from the diff. Never invent content to fill a section. An empty section is deleted, not filled.**

**R1 — Group by flow, not by commit.**
Group changes into user-facing scenarios or feature flows (`## {flow name}`). One flow spans however many files it needs — data serving (file execution or API call) → state/hook/store → UI rendering. Never order bullets by commit sequence.
If there is only one group, omit the `##` heading and write the bullets directly under `## 변경사항`.

**R2 — Prose and bullets only. No diagrams.**

The PR body carries no mermaid blocks, ASCII art, or images. If a flow is too tangled to state in bullets, that is a signal to split the group — not to draw it.

**R3 — Bullet form.**
`{대상} — {무엇이 어떻게}`, ending in a noun phrase. State only what the diff shows. Do not describe intent, expected benefit, or effort.

Banned phrasings (delete the bullet if nothing survives): 전반적으로, ~등을 개선, 안정성 향상, 가독성 향상, 코드 정리, 리팩터링 진행, 로직 수정, 기능 보완.

**R4 — Backticks are for identifiers only.**
Use them for: file paths, function/component/type/variable names, CLI commands, environment variables, HTTP endpoints.
Do not use them for: Korean nouns in prose, feature names, screen names, library names used as a sentence subject, or any phrase that reads as natural language.
Hard check: if one bullet needs more than 3 backticked spans, rewrite it — that means it lists identifiers instead of describing a flow.

**R5 — Length ceiling.**
Max 5 bullets per group. If a group exceeds it, split the group or drop the minor details. Do not pad a short PR.

**R6 — `###` sub-headings carry "why" only.**
Under a group, a `###` block explains a judgment call or trade-off that the bullets cannot: why this approach over the obvious alternative, what cost it accepts. If it restates a bullet, delete it.

**R7 — Conditional sections.**
`## 구현 화면` and `## 테스트 케이스` are emitted only when their trigger is met. When not met, delete the heading and its `---` separator entirely. Never write `없음`, never leave an empty checkbox list, never leave an empty table.

`## 구현 화면` trigger: the diff changes rendered UI. Leave the table rows blank for the user.

`## 테스트 케이스` trigger: `tasks.md` records that testing actually happened. This section transcribes evidence; it never generates scenarios.

Locate `tasks.md` — prefer one changed by this branch, otherwise the `docs/*/plans/tasks.md` matching the branch topic:

```bash
git diff origin/{PR_BASE}..{HEAD_BRANCH} --name-only -- '**/tasks.md'
```

Read its `## 진행 기록` entries and its checklists, then include only what counts as evidence:
- a `## 진행 기록` entry describing a scenario that was verified, manually or automatically
- a recorded test command and its result (suite run, e2e run, build check)
- a checked-off item that is itself a test or QA step

Not evidence — omit the section if this is all that exists:
- unchecked boxes, or items phrased as intent (`테스트 예정`, `확인 필요`)
- test files appearing in the diff — adding a test is not proof of running it
- implementation items that merely imply the feature works

If no `tasks.md` exists, or it holds no evidence, delete the section. Do not ask the user to supply scenarios, and do not restate a scenario in stronger terms than the record supports.

---

### Confirm and create

Two review modes. Use **preview-file mode** when `--preview` is in `$ARGUMENTS` or the user asked to review the PR as a markdown document (`미리보기 문서로 먼저 보여줘`, `md로 확인하고 생성해줘`, and similar). Otherwise use inline mode.

Always pass the body via `--body-file`, never `--body "{BODY}"` — a body containing backticks, quotes, or `$` does not survive shell interpolation.

#### Inline mode

Show the generated title and body to the user in plain conversation (in Korean), then call `AskUserQuestion` with:
- prompt: `"PR 초안을 확인해주세요. 이대로 생성할까요?"`
- options: `["생성", "수정할게요 — 수정 후 다시 확인"]`

If `수정할게요` is chosen, ask what to change in plain conversation, apply the edits, and show the updated draft again. Repeat until confirmed.

On confirmation, write the body to `{REPO_ROOT}/.pr-body.tmp.md` and go to [Create the PR].

#### Preview-file mode

Resolve the repository root:

```bash
git rev-parse --show-toplevel
```

Write the draft to `{REPO_ROOT}/.pr-preview.md` with this exact layout — the preamble is for the user only and never reaches the PR:

```markdown
<!-- /git-pr PR 미리보기 — 생성이 끝나면 이 파일은 자동 삭제됩니다 -->

# {TITLE}

- head: `{HEAD_BRANCH}`
- base: `{PR_BASE}`

이 파일을 직접 수정해도 됩니다. 수정 후 대화에서 "생성"을 고르면 수정된 내용 그대로 올라갑니다.

<!-- ↓↓↓ PR 본문 시작 ↓↓↓ -->

{BODY}
```

Everything below the `<!-- ↓↓↓ PR 본문 시작 ↓↓↓ -->` marker is the PR body, verbatim. The marker line is the only delimiter — do not rely on `---` separators, which occur inside the body itself.

Then tell the user in Korean: the absolute file path, and that they should open it in their editor's markdown preview to check it. Call `AskUserQuestion` with:
- prompt: `"미리보기 문서를 확인해주세요. 이대로 PR을 생성할까요?"`
- options: `["생성 — 미리보기 파일은 삭제됨", "수정할게요 — 파일을 직접 고쳤거나 요청할 내용이 있음"]`

If `수정할게요` is chosen: **re-read `.pr-preview.md` first** — the user may have edited it directly. Apply any additional requests they state in conversation on top of the file's current content, rewrite the file, and ask again. Repeat until confirmed.

On confirmation, re-read `.pr-preview.md` one final time, and write everything after the marker line to `{REPO_ROOT}/.pr-body.tmp.md`.

#### Create the PR

**Primary PR:**

```bash
gh pr create --head {HEAD_BRANCH} --base {PR_BASE} --title "{TITLE}" --body-file "{REPO_ROOT}/.pr-body.tmp.md"
```

**Secondary PR** (only when an additional PR was requested):

```bash
gh pr create --head {ORIGIN_BRANCH} --base {ALSO_PR_TARGET} --title "{TITLE}" --body-file "{REPO_ROOT}/.pr-body.tmp.md"
```

#### Clean up

Only after every requested PR has been created successfully:

```bash
rm -f "{REPO_ROOT}/.pr-body.tmp.md" "{REPO_ROOT}/.pr-preview.md"
```

If `gh pr create` fails, leave both files in place, report the error in Korean, and let the user retry from the existing preview.

Capture and display all PR URLs.

---

## Report

Summarize the completed work in Korean:
- Changes: committed / stashed (when applicable)
- Branch: created or pushed (include name and base)
- Sub-branch: created and pushed (when a suffix was used)
- Rebase: onto `origin/{BASE}` (when a rebase ran)
- PR: list of URLs (when the PR Phase ran)
- Preview file: deleted (when preview-file mode ran)

---

## Base branch resolution

When the user selects `master (or main)`, determine which name actually exists in the repository.

1. Query both candidates on the remote:

   ```bash
   git ls-remote --heads origin master main
   ```

2. Decide:
   - **Only one exists** → use that name as `BASE` (do not ask the user)
   - **Both exist** → ask via `AskUserQuestion`:
     - prompt: `"원격에 master와 main이 모두 있어요. 어느 쪽을 사용할까요?"`
     - options: `["master", "main"]`
   - **Neither exists** → tell the user in Korean: `"원격에 master/main 브랜치가 없어요. 브랜치명을 직접 입력해주세요."` and wait for input

3. Store the resolved value in `BASE` and continue.

---

## Rules

- Never delete remote branches
- Use `--force-with-lease` — never bare `--force`
- If rebase has conflicts, resolve them (Read conflicting files → Edit to fix → `git add` → `git rebase --continue`); only abort if resolution is impossible
- Always return to `{ORIGIN_BRANCH}` after sub-branch work
- Only auto-stage with explicit user confirmation (`전체 스테이징 후 커밋`)
- Always generate PR title and body from commit log and diff analysis — never use `--fill`
- Follow the PR body authoring rules (R1–R7); they override any habit of filling every section
- Never write `없음`, an empty checklist, or an empty table — delete the section instead
- Never put a mermaid block, ASCII art, or an image in the PR body
- Always pass the PR body with `--body-file`, never `--body "{BODY}"`
- Never `git add` or commit `.pr-preview.md` / `.pr-body.tmp.md`; delete them only after the PRs are created
- Do not fill in the `구현 화면` table rows — leave them blank for the user
- Never claim a test was run or a scenario was verified unless `tasks.md` records it
- If `gh` is not installed, stop and tell the user in Korean
- All user-facing messages and questions must be in Korean
