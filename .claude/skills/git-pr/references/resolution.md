# Issue Number & Base Branch Resolution

Two lookups the PR phase needs only sometimes. Read this when you reach the step that calls for it.

## Contents

- [Issue number resolution](#issue-number-resolution)
- [Base branch resolution](#base-branch-resolution)

## Issue number resolution

The PR title carries the issue number as a `[{ISSUE_NO}]` prefix. Resolve it in this order and stop
at the first hit.

1. **Flags** — `--no-issue` in `$ARGUMENTS` → no prefix, skip the rest. `--issue <no>` → use that
   value verbatim.

2. **`tasks.md` header** — the `> 이슈:` field written by `/task-plan`, the authoritative source
   when the branch has a plan document. Locate the file the same way `## 테스트 케이스` does, then:

   ```bash
   grep -m1 '^> 이슈:' {TASKS_MD}
   ```

   Use the value unless it is `없음` or empty.

3. **Branch name** — match `HEAD_BRANCH` against a Jira-style key: 2–10 letters, a hyphen, then
   digits, standing as its own segment.

   ```bash
   echo "{HEAD_BRANCH}" | grep -oE '(^|[/_-])[A-Za-z]{2,10}-[0-9]+([/_-]|$)' | head -1
   ```

   Strip the surrounding delimiters and uppercase the result (`abc-123` → `ABC-123`). Do not ask
   the user to confirm it.

   > Only this pattern counts. A bare number elsewhere in the branch name (`feat/v2-migration`,
   > `fix/500-error`) is not an issue number — fall through to the next step.

4. **Ask** — offer two choices:
   - prompt: `"PR 제목에 붙일 이슈 번호를 알려주세요."`
   - options: `["직접 입력 — 이슈 번호를 입력하면 제목 앞에 [번호]로 붙임", "없음 — 이슈 번호 없이 제목만 사용"]`

   On `직접 입력`, ask for the number in plain conversation (in Korean) and use it verbatim.

## Base branch resolution

When the user selects `master (or main)`, determine which name actually exists in the repository.

1. Query both candidates on the remote:

   ```bash
   git ls-remote --heads origin master main
   ```

2. Decide:
   - **Only one exists** → use that name as `BASE` (do not ask the user)
   - **Both exist** → ask:
     - prompt: `"원격에 master와 main이 모두 있어요. 어느 쪽을 사용할까요?"`
     - options: `["master", "main"]`
   - **Neither exists** → tell the user in Korean:
     `"원격에 master/main 브랜치가 없어요. 브랜치명을 직접 입력해주세요."` and wait for input

3. Store the resolved value in `BASE` and continue.
