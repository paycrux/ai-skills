---
name: git-pr
description: "Full Git PR workflow: choose git-only, PR-only, or both. Branch modes: create fresh branch from base, or commit/push current branch with optional suffix sub-branch and rebase. Handles staged and unstaged changes. Use /git-pr [--mode git|pr|both] [--new <name>] [--suffix <dev|stg>] [--base <branch>] [--no-rebase] [--also-pr <branch>]"
argument-hint: "[--mode git|pr|both] [--new <name>] [--suffix <dev|stg>] [--base <branch>] [--no-rebase] [--also-pr <branch>]"
disable-model-invocation: true
allowed-tools: Bash, AskUserQuestion
---

# /git-pr — Git PR Workflow

## Step 1: 무엇을 할까요?

If `--mode` is not in `$ARGUMENTS`, call `AskUserQuestion` with:
- prompt: `"어떤 작업을 진행할까요?"`
- options: `["git — 브랜치 작업만 (PR 생성 없음)", "pr — PR만 생성 (현재 브랜치 기준)", "both — 브랜치 작업 + PR 생성"]`

If `--mode git|pr|both` is provided, skip Step 1.

---

## Step 2: 브랜치 방식 (mode가 `pr`이면 건너뜀)

Call `AskUserQuestion` with:
- prompt: `"브랜치를 어떻게 할까요?"`
- options: `["새 브랜치 생성 — base 브랜치(develop/master(or main)/staging)에서 새로 분기", "현재 브랜치 사용 — 커밋·푸시 후 선택적으로 서브 브랜치 생성 및 리베이스"]`

If `--new <name>` is in `$ARGUMENTS` → New branch mode, skip Step 2.
If `--suffix` or no branch flags → Current branch mode, skip Step 2.

---

## Step 3: 작업 트리 변경사항 처리 (mode가 `pr`이면 건너뜀)

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

### Case A: staged + unstaged 둘 다 있음

Call `AskUserQuestion` with:
- prompt: `"스테이징된 변경사항과 스테이징 안 된 변경사항이 모두 있어요. 어떻게 처리할까요?"`
- options: `["전체 스테이징 후 커밋 — git add -A 후 커밋", "스테이징된 것만 커밋 — 스테이징 안 된 변경사항은 그대로 유지", "전체 스태시 — git stash로 임시 보관 후 브랜치 작업 완료 뒤 복원"]`

### Case B: staged만 있음

Ask for commit message via plain conversation (한국어로 커밋 메시지를 입력해달라고 요청), then commit:

```bash
git commit -m "<message>"
```

### Case C: unstaged만 있음 (staged 없음)

Call `AskUserQuestion` with:
- prompt: `"스테이징 안 된 변경사항이 있어요. 어떻게 처리할까요?"`
- options: `["전체 스테이징 후 커밋 — git add -A 후 커밋", "스태시 — git stash로 임시 보관 후 브랜치 작업 완료 뒤 복원", "그냥 진행 — 변경사항 유지한 채로 진행 (현재 브랜치 모드에서만 가능)"]`

> **새 브랜치 모드:** "그냥 진행"은 선택 불가 — 브랜치 전환 시 클린 상태 또는 스태시 필요.

### Case D: 클린

변경사항 없음, 계속 진행.

---

## Mode A — 새 브랜치 생성

### A1: 옵션 수집

If not provided via flags:
- Ask for branch name via plain conversation: 한국어로 `"새 브랜치 이름을 입력해주세요"` 라고 요청
- Call `AskUserQuestion` with:
  - prompt: `"어느 브랜치에서 분기할까요?"`
  - options: `["develop", "master (or main)", "staging"]`

> `master (or main)` 선택 시 아래 **Base 브랜치 해석** 절차로 실제 브랜치명을 결정한다.

### A2: 실행

```bash
git fetch origin {BASE}
git checkout -b {NEW_BRANCH} origin/{BASE}
git push -u origin {NEW_BRANCH}
```

If stash was used in Step 3: `git stash pop`

Set `HEAD_BRANCH = {NEW_BRANCH}`.

If mode is `git` → [리포트], done.
If mode is `both` → [PR Phase].

---

## Mode B — 현재 브랜치 사용

### B1: 옵션 수집

If not provided via flags:
- Call `AskUserQuestion` with:
  - prompt: `"서브 브랜치 suffix를 붙일까요? (예: feat/my-feature-dev)"`
  - options: `["dev — -dev 붙여서 서브 브랜치 생성", "stg — -stg 붙여서 서브 브랜치 생성", "없음 — 서브 브랜치 생성 안 함"]`
- Call `AskUserQuestion` with:
  - prompt: `"어느 브랜치 기준으로 리베이스할까요?"`
  - options: `["develop", "master (or main)", "staging", "리베이스 안 함"]`

> `master (or main)` 선택 시 아래 **Base 브랜치 해석** 절차로 실제 브랜치명을 결정한다.

### B2: 현재 브랜치 확인

```bash
git branch --show-current
```

Save as `ORIGIN_BRANCH`.
If suffix set: `SUB_BRANCH = {ORIGIN_BRANCH}-{suffix}`.

### B3: 원본 브랜치 푸시

```bash
git push origin {ORIGIN_BRANCH}
```

### B4: 서브 브랜치 생성 (suffix 설정 시에만)

```bash
git branch -D {SUB_BRANCH} 2>/dev/null || true
git checkout -b {SUB_BRANCH}
```

> 원격 서브 브랜치는 절대 삭제하거나 건드리지 않음.

### B5: 리베이스 (`없음` 또는 `--no-rebase`이면 건너뜀)

```bash
git fetch origin {BASE}
git rebase origin/{BASE}
```

충돌 발생 시:

1. 충돌 파일 목록 확인:
   ```bash
   git diff --name-only --diff-filter=U
   ```

2. 각 충돌 파일을 Read로 열어 `<<<<<<< HEAD`(내 브랜치)와 `=======` 이후(base 브랜치) 양쪽 변경사항을 분석한다:
   - 변경의 **의도**를 파악한다 — 어느 쪽이 새 기능 추가인지, 버그 픽스인지, 리팩터인지
   - 양쪽을 모두 살려야 하는 경우(both-side merge)인지, 한쪽을 택해야 하는 경우인지 판단한다
   - 판단 근거와 함께 제안 해결안을 한국어로 설명한다

3. `AskUserQuestion`으로 사용자에게 제안을 보여주고 승인을 받는다:
   - prompt: `"[파일명] 충돌 해결 제안입니다. [판단 근거 + 제안 내용]. 이대로 진행할까요?"`
   - options: `["이대로 진행", "직접 수정할게요 — 잠시 후 계속 진행해주세요"]`

4. 승인 시 Edit으로 충돌 마커를 제거하고 제안 내용으로 파일을 수정한다. "직접 수정" 선택 시 사용자가 완료 후 알려줄 때까지 대기한다.

5. 충돌 해결 후:
   ```bash
   git add {resolved_files}
   git rebase --continue
   ```

6. 추가 충돌이 있으면 2–5 반복. 최종 성공까지 계속 진행한다.

### B6: 푸시

```bash
git push --force-with-lease origin {SUB_BRANCH or ORIGIN_BRANCH}
```

### B7: 원본 브랜치로 복귀 (suffix 설정 시에만)

```bash
git checkout {ORIGIN_BRANCH}
```

If stash was used in Step 3: `git stash pop`

`HEAD_BRANCH` = `{SUB_BRANCH}` if suffix set, else `{ORIGIN_BRANCH}`.

If mode is `git` → [리포트], done.
If mode is `both` → [PR Phase].

---

## PR Phase (mode `pr` 또는 `both`)

If mode is `pr` (no branch work done):

```bash
git branch --show-current
```

Set `HEAD_BRANCH` = current branch.

### PR 옵션 수집

Call `AskUserQuestion` with:
- prompt: `"PR의 대상 브랜치(base)를 선택해주세요."`
- options: `["develop", "master (or main)", "staging"]`

> `master (or main)` 선택 시 아래 **Base 브랜치 해석** 절차로 실제 브랜치명을 결정한다.

Call `AskUserQuestion` with:
- prompt: `"추가로 다른 브랜치에도 PR을 생성할까요? (예: develop → staging 동시 PR)"`
- options: `["없음 — PR 하나만 생성", "직접 입력 — 대상 브랜치를 입력해서 추가 PR 생성"]`

```bash
gh auth status
```

If not authenticated: 한국어로 `gh auth login` 실행을 안내하고 중단.

### PR 초안 생성

Run the following to analyze the branch changes:

```bash
git log origin/{PR_BASE}..{HEAD_BRANCH} --oneline
```

```bash
git diff origin/{PR_BASE}..{HEAD_BRANCH} --stat
```

Using the commit log and diff stat, generate:

1. **PR title** — concise summary of what this PR does (Korean allowed)
2. **PR body** — fill in all sections below based on the commits and changes. Leave 구현 화면 blank for the user to fill in.

PR body template:

```
## 구현사항

{Fill based on commit log and diff — bullet list of what was implemented}

---

## 특이사항

{Fill if there are known limitations, temporary workarounds, or behavior changes. Write "없음" if none.}

---

## 핵심 리뷰 포인트

{Fill with the most important areas for reviewers to focus on — key logic changes, risky areas, design decisions}

---

## 구현 화면

> UI 변경이 없으면 삭제

| Before | After |
|--------|-------|
|        |       |

---

## 테스트 케이스

{Fill with a checklist of scenarios verified — keep it concise, no need for excessive detail}

- [ ]
- [ ]
```

Show the generated title and body to the user in plain conversation (Korean), then call `AskUserQuestion` with:
- prompt: `"PR 초안을 확인해주세요. 이대로 생성할까요?"`
- options: `["생성", "수정할게요 — 수정 후 다시 확인"]`

If "수정할게요" → ask what to change in plain conversation, apply edits, and show the updated draft again. Repeat until confirmed.

**Primary PR:**

```bash
gh pr create --head {HEAD_BRANCH} --base {PR_BASE} --title "{TITLE}" --body "{BODY}"
```

**Secondary PR** (only if 추가 PR 선택 시):

```bash
gh pr create --head {ORIGIN_BRANCH} --base {ALSO_PR_TARGET} --title "{TITLE}" --body "{BODY}"
```

Capture and display all PR URLs.

---

## 리포트

완료된 작업 요약 (한국어로):
- 변경사항: 커밋됨 / 스태시됨 (해당 시)
- 브랜치: 생성/푸시됨 (이름 및 base 포함)
- 서브 브랜치: 생성 및 푸시됨 (suffix 사용 시)
- 리베이스: `origin/{BASE}` 기준 (리베이스 실행 시)
- PR: URL 목록 (PR Phase 실행 시)

---

## Base 브랜치 해석

사용자가 `master (or main)`을 선택한 경우, 실제 리포지토리에 어떤 브랜치명이 존재하는지 확인한다.

1. 원격에서 두 후보를 조회:

   ```bash
   git ls-remote --heads origin master main
   ```

2. 판정:
   - **한쪽만 존재** → 그 이름을 `BASE`로 사용 (사용자에게 묻지 않음)
   - **둘 다 존재** → `AskUserQuestion`으로 선택받기:
     - prompt: `"원격에 master와 main이 모두 있어요. 어느 쪽을 사용할까요?"`
     - options: `["master", "main"]`
   - **둘 다 없음** → 한국어로 `"원격에 master/main 브랜치가 없어요. 브랜치명을 직접 입력해주세요."` 안내 후 사용자 입력 대기

3. 결정된 값을 `BASE`에 저장하고 다음 단계 진행.

---

## Rules

- Never delete remote branches
- Use `--force-with-lease` — never bare `--force`
- If rebase has conflicts, resolve them (Read conflicting files → Edit to fix → `git add` → `git rebase --continue`); only abort if resolution is impossible
- Always return to `{ORIGIN_BRANCH}` after sub-branch work
- Only auto-stage with explicit user confirmation (`전체 스테이징 후 커밋`)
- Always generate PR title and body from commit log analysis — never use `--fill`
- Do not fill in 구현 화면 section — leave it blank for the user
- If `gh` is not installed, stop and tell the user in Korean
- All user-facing messages and questions must be in Korean
