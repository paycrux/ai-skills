---
name: tracker
description: "Control session for a feature that spans several Jira stories. Given Notion + Jira story + Figma links once, it writes a meta-plan, creates [프론트] dev sub-issues, opens one top-level worktree per story, and then drives the work: whenever an issue's next step is a skill (/task-plan, /implement), it runs it — itself when the story worktree is this session's, by message to the session that owns that worktree otherwise — and keeps going until a person has to decide. Use when the user runs /tracker, or hands over planning links for work across several stories."
argument-hint: "[notion url] [jira story links] [figma links] — or nothing, to continue"
---

# /tracker — 관제 세션

A feature that spans several Jira stories is several branches at once. Git keeps them apart until
they merge, but every worktree is a folder on the same disk: any session can read any worktree's
`tasks.md` and `git log` by absolute path. The tracker is built on that.

The tracker keeps the meta-plan, the Jira issues, the branches and worktrees — and it **drives**
the work. When an issue's next step is a skill, the tracker runs it: itself, when the issue lives in
this session's worktree; by message, when another session owns that worktree. It keeps going until
a person has to decide something, then reports.

```
/tracker <노션> <지라 스토리들> <피그마>   ← 처음 한 번
/tracker                                   ← 그다음부터 계속 이것만
```

**Never tell the user to type a skill this session could run.** "이 탭에서 `/implement`를
실행하세요" is a failure when this tab is the tracker's own.

## Default layout — unless the user asks for another

| 대상 | 워크트리 | 브랜치 |
|---|---|---|
| 스토리 | orca **최상위** 워크트리 하나 (`--no-parent`) — /tracker를 어느 워크트리에서 실행했든 | `feat/<스토리 키>`, `origin/<루트>`에서 |
| 스토리의 `[프론트]` 하위 이슈 | 따로 없음 — 스토리 워크트리 안에서 `git switch`로 한 번에 하나씩 | `feat/<하위 키>`, 스토리 브랜치에서 |
| 스토리 여러 개가 쓰는 공용 / 치명적 공유 컴포넌트 수정 | 각자 최상위 워크트리 | `feat/<키>` / `fix/<키>`, `origin/<루트>`에서 |

orca files a new worktree under whatever workspace the command runs in, so a story created from
inside another worktree lands as that worktree's child unless `--no-parent` is passed. Child
worktrees per sub-issue, chained branches, or any other arrangement happen only when the user asks;
record the arrangement in the meta-plan's `워크트리:` header and follow it from then on.

## Who does what

Each story worktree has one **owner**: the Claude session whose working directory is that worktree.
When this tracker session runs inside a story worktree, the tracker *is* that story's owner.

| | tracker | owner (when it is a different session) |
|---|---|---|
| 쓰는 것 | 메타 플랜, 지라, 브랜치·워크트리 | 자기 계획 문서·코드·커밋 |
| 하는 일 | 상태 읽기, 다음 단계 실행 또는 지시, 지라 전환·댓글 | `/task-plan`, `/implement`, 커밋, 기기 확인 체크리스트 |
| 묻는 것 | 메타 플랜 검토, 이슈 목록, 루트, 워크트리 배치, 공유 컴포넌트 판단 | 계획 검토, 작업 중 막힌 질문 |

When the tracker is the owner, it does both columns. Blocker questions are asked by whoever is
doing the work, in that tab — the tracker never relays them. Completion is decided from files, never
from a session's reply.

## What running /tracker authorizes

- Running `/task-plan` and `/implement` for issues in this meta-plan, or telling their owners to
- Committing an issue's work as soon as implementation finishes
- `git push --force-with-lease` on a branch in this meta-plan's 작업 트리, after a rebase
- Jira: create issues once the list is approved; comment on them; move them toward `개발진행중` / `개발 완료`

Never: commit, push, or force-push to the root; touch a branch not in the 작업 트리; edit a story's
description (backend, 기획, and design share the story).

## Step 1: Find the work

The repo is the first entry of `git worktree list --porcelain`. The tracker may run from any
worktree; it reaches every other one by absolute path. Never `EnterWorktree` from here — a second
`orca worktree create` from inside an entered worktree is refused by the isolation guard.

- **Arguments contain links** → **A**.
- **No arguments** → look for `docs/*/meta-plan.md` in the repo and in every worktree. The same
  meta-plan (same `기획:` link) can appear on several branches; the copy on the branch its
  `문서 위치:` header names is the real one. Take the one whose 작업 트리 still has a row that is not
  `병합`. Several → ask which. None → say so and stop.

### Orchestration rung — detect it, never guess it

Whether the tracker can open a session for another worktree or can only print a command depends on
the host. A session that finds this out by trying gives a different answer every run, and the user
cannot tell what made the difference. Probe once, write the answer into the meta-plan's
`오케스트레이션:` header, and open every report with it.

```bash
command -v orca        # 등급 1이 되려면 있어야 한다
```

| 등급 | 조건 | 다른 워크트리의 다음 단계를 |
|---|---|---|
| 1 | orca 있음 + 호스트가 세션 목록·메시지를 제공 | tracker가 탭을 열고 지시까지 |
| 2 | 세션 목록·메시지만 | 이미 열린 탭에 지시. 없는 탭은 사용자가 열어준다 |
| 3 | 둘 다 없음 | `cd <wt>`와 지시문을 출력하고 사용자가 붙여넣는다 |

Re-probe only when a rung's own mechanism fails — a message that does not arrive, `orca terminal
create` that errors. A failure drops the header one rung and says so in the report; it never falls
back silently.

## Step 2: Read the state

For every 작업 트리 row:

- **Plan** — the `docs/*/plans/tasks.md` whose `> 이슈:` header is this row's key. A branch carries
  every plan from its base, so match by key. A sub-issue branch that is not checked out right now is
  read with `git -C <wt> show feat/<KEY>:<path>`.
- **Progress** — checked / total under the `## Phase` headings; every `**blocker**` line; the
  `## 기기 확인` checklist, if present.
- **Commits** — `git -C <wt> log --oneline <기준 커밋>..feat/<KEY>`; uncommitted changes with
  `git -C <wt> status --porcelain` when the branch is checked out.
- **PR** — `gh pr list --head <branch> --state all --json number,state,baseRefName`.
- **Jira** — every row's status in one call:
  `acli jira workitem search --jql "key in (<작업 트리의 키 전부>)" --fields key,status --json`.
  The tracker reads Jira as well as writing it. Without the read a failed transition, or a person
  moving an issue by hand, leaves no trace anywhere.

| 관측 | 상태 |
|---|---|
| 브랜치 없음 | 대기 |
| `tasks.md` 있음, 체크 0 | 계획 |
| 체크 1개 이상, 남은 항목 있음 | 구현 |
| Phase 전부 체크 + 커밋 있음 + `## 기기 확인` 남음 | 확인 |
| `## 기기 확인` 전부 체크 (웹: `qa-report.md`에 미해결 버그 없음) | 완료 |
| PR 열림 / 병합됨 | PR / 병합 |

**Files win.** Correct the meta-plan when it disagrees with the files and carry on. When the
disagreement has no explanation you can verify — a branch gone, work unaccounted for — stop and
report instead of guessing.

**Jira follows the files.** Behind what the files say — an issue still `개발예정` while items are
checked — walk it forward (**F**) and put one line in the report: `COMP-408 지라를 개발진행중으로
맞춤`. Ahead of the files — someone moved it to `개발 완료` while items are unchecked — do not move
it back; report the difference and let the user decide. Either way the 지라 column of the report
carries what Jira actually said this run, not what the tracker last wrote.

## Step 3: Drive — run the next step

Pick each story's active issue — the first row, in 작업 트리 order, that is not `PR` or `병합` —
and do what its state calls for:

| 상태 | 다음 | 누가 |
|---|---|---|
| 대기 | 스토리 워크트리에서 `git switch -c feat/<KEY> feat/<STORY>`(이미 있으면 `git switch feat/<KEY>`) → `/task-plan` with the meta-plan path and `<KEY>` | owner |
| 계획, 검토 전 | `/task-plan`의 검토 요청에 사용자가 답할 때까지 대기 | 사람 |
| 계획, 승인됨 | `/implement <slug>` | owner |
| 구현, 멈춰 있고 답을 기다리는 blocker 없음 | `/implement <slug>` 재개 | owner |
| Phase 전부 체크, 커밋 안 됨 | 커밋 | owner |
| 확인 | 사용자가 `## 기기 확인` 체크 | 사람 |
| 완료 | **F** | tracker |
| PR 열림 | 커밋이 끝났으면 다음 하위 이슈로 — 표의 첫 줄부터 | tracker |

**How to run a step:**

- **The owner is this session** → invoke the skill with the Skill tool, now, in this turn.
- **The owner is another session** → send it the instruction —
  `${CLAUDE_SKILL_DIR}/templates/kickoff.template.md` for an issue's first step, one line
  (`[tracker] {KEY} — /implement {slug} 재개`) for a resume — with an idle subscription where the
  host offers one.
- **No owner yet** → start one (**D**), then send.

**Plan approval.** `/task-plan` ends by handing its plan back and stopping; that review is a real
gate. The moment the user approves — "좋아", "진행해", "이대로" — the owner starts `/implement` in
the same turn. Coming back to a plan at 0 checked with no record of approval, show a three-line
summary and ask once: `이대로 구현을 시작할까요?` A yes starts `/implement` immediately.

**Keep going.** After a step finishes — a skill this session ran returns, a report or idle notice
arrives from an owner — run Step 2 and Step 3 again. Stop only at a person-shaped gate: plan review,
a blocker question, 기기 확인, a PR to open, or one of **When the tracker stops**. Then report:

```
오케스트레이션 등급 {N} — {한 줄}

| 이슈 | 상태 | 지라 | 커밋 | blocker | 다음 |
| --- | --- | --- | --- | --- | --- |
| COMP-408 [프론트] 서비스 문의 | 구현 12/40 | 개발진행중 | 2 | 1 — Android 13+ 사진 권한 | COMP-364 탭에서 답변 대기 |
| COMP-415 [프론트] 공지사항 | 대기 | 계획 | 0 | - | COMP-408 PR 뒤 자동 시작 |

방금 한 것: {tracker·owner가 실행한 것} / 사용자가 할 것: {탭 이름·체크할 목록·명령까지}
```

## A. Write the meta-plan

One 기획서, one meta-plan. Given several, ask which to start with. Derive `{name}` — a kebab-case
English slug from the Notion title — and confirm it.

**기획서**

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url>" \
  --output "<repo>/docs/{name}/기획-snapshot.md" --metadata /tmp/tracker-source.json --check-auth
```

The script replaces Notion's signed image URLs with a placeholder. Split on `## ` headings ignoring
leading whitespace — a Notion column layout indents them.

**Keep the fetched markdown.** `docs/{name}/기획-snapshot.md` is committed next to the meta-plan and
moves with it. It is the only record of what the 기획서 said when the scope was cut, and **G** diffs
against it — hand-editing it makes that diff lie. From `--metadata`'s JSON take `last_edited_time`
into the `기획 스냅샷:` header. A 기획서 split across sub-pages gets one snapshot file and one header
line per page: editing a child page does not move the parent's `last_edited_time`.

**스토리와 기존 하위 이슈**

```bash
acli jira workitem view <STORY> --fields summary,issuetype,status,parent,description --json
acli jira workitem search --jql "parent = <STORY>" --fields key,summary,issuetype,assignee,status --json
```

An existing `[개발]` sub-issue assigned to the user is reused; anyone else's is left alone.

**디자인 — shallow only.** `get_metadata` frame by frame: a section node can exceed 100K
characters, so go one level down. `get_screenshot` only when a frame name is useless. Never
`get_design_context` here. Record frame names and IDs, modal and state frames included.

**스토리 = 범위.** Map 기획 sections → stories → frames; the 기획서 often states its own split.
Report both gaps: a 기획 section no story takes, a story no 기획 section covers.

**사용자 노출 문구** — every snackbar, modal, button, and error string, verbatim, per story, with the
dev issue that renders it. A missing string goes on the story's `미정` line.

**개발 이슈** — every story gets exactly one `[프론트] <화면·기능>` sub-issue, even a small one: the
story is shared with backend, 기획, and design. More than one only on the condition in **B** — the
기획서 itself separates the story into independently shipping screens. Create `[백엔드]` or other
sub-issues only when the user asks.

**범위 간 공유물** — promote only when the 기획서 shows the same element in two or more places (same
문구 row, same Figma node). Across stories → a 공용 issue and its own worktree; within one story →
built on the story branch; app-wide primitives → not edited (**E**).

**Write** it from `${CLAUDE_SKILL_DIR}/templates/meta-plan.template.md`, in Korean. The meta-plan is
**version-controlled**: draft it at `<repo>/docs/{name}/meta-plan.md`, and once the first story
worktree exists (**C**), move it there and commit it on the story branch (`docs:`). It reaches the
root with that story's PR. A meta-plan spanning several stories lives on the first story's branch;
the others read it by absolute path. Record the branch in the `문서 위치:` header. Later edits ride
along with the owner's next commit on that worktree.

**Root** — the branch other developers share. Reuse the `루트:` of another meta-plan in this repo;
otherwise ask once. Do not derive it from a rule like "develop, else the default branch".

Then **stop**. Nothing is in Jira yet.

```
메타 플랜을 작성했습니다.

- 문서: `{path}` (스토리 워크트리가 생기면 `feat/{STORY}`로 옮겨 커밋)
- 스토리 {N}개, 개발 이슈 {M}개 (새로 만들 것 {K}개), 공용 {J}개
- 어디에도 안 붙은 기획: {N}건 / 기획이 없는 스토리: {N}건 / 미정: {N}건   ← 있을 때만

검토하시고 고칠 부분을 알려주세요. 괜찮으면 만들 지라 이슈 목록을 보여드립니다.
```

## B. Create the Jira issues

**One `[프론트]` sub-issue per story.** That is the default, and it does not depend on how big the
story looks. Split into more only when the 기획서 itself separates the story into screens or features
that ship independently — and then the 근거 column names the section that separates them. "이슈가 커
보인다" is not a 근거. An existing `[개발]` sub-issue assigned to the user is reused; anyone else's is
left alone.

Ask with `${CLAUDE_SKILL_DIR}/templates/issue-list.template.md`, unchanged. The wording is fixed so
that the same scope produces the same question in every session — filling the table is the only work.
Then **stop for approval**: an issue is visible to the whole team the moment it exists.

The only answers that change the list are 추가 · 삭제 · 제목 · 분할. Nothing else is asked here — not
the assignee, not the order, not labels, not whether to create them at all.

For each approved issue, re-check the parent has no sub-issue with the same summary, then:

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/jira/md_to_adf.py" /tmp/tracker-<slug>.md -o /tmp/tracker-<slug>.adf.json
acli jira workitem create --project <PROJECT> --type "[개발]" --parent <STORY> \
  --summary "[프론트] <화면·기능>" --assignee @me \
  --description-file /tmp/tracker-<slug>.adf.json --json
```

The markdown comes from `${CLAUDE_SKILL_DIR}/templates/dev-issue.template.md` (`## 기획 리뷰`).
Sub-issue type names differ per project — read them from `acli jira project view --key <PROJECT>
--json`. Write every key into the 작업 트리.

## C. Worktrees and branches

Take the root from the remote — a local copy can be commits behind:

```bash
git -C <repo> fetch origin <root>
```

**Story worktree — orca, top-level:**

```bash
orca worktree create --name "<STORY>" --repo "path:<repo>" --base-branch "origin/<root>" --no-parent --json
orca worktree list --json     # 방금 만든 워크트리에 상위 워크트리가 없어야 한다
git -C "<wt>" branch -m "$(git -C "<wt>" branch --show-current)" "feat/<STORY>"
git -C "<wt>" branch --unset-upstream 2>/dev/null
```

- **The top-level check is not optional.** orca files a new worktree under whatever workspace the
  command runs in, so a story created from inside another worktree becomes that worktree's child
  unless `--no-parent` holds. Run `orca worktree list --json` right after creating and read this
  story's entry. It has a parent → `orca worktree set --worktree "path:<wt>" --no-parent`, then read
  it again. Still there → stop and report; work does not start in a nested worktree.
- **Jira's 부모 and orca's 상위 워크트리 are different axes.** A sub-issue branching off the story
  branch is a statement about branches, and says nothing about where the worktree sits: worktrees
  stay one per story, top-level. In this document 부모 refers to a Jira issue only; a worktree's is
  always called 상위 워크트리.
- orca has no branch-name option and prefixes the GitHub login (`AeiYo/COMP-364`); the rename gives
  `feat/<STORY>`. `orca worktree list` can keep showing the old name for a while — `git worktree
  list` is the source of truth.
- A branch cut from `origin/<root>` tracks the root; unset it so a bare `git push` can never go
  there.
- `--repo` takes the original checkout's absolute path — `git rev-parse --show-toplevel` inside a
  worktree returns that worktree instead.
- orca's setup hook runs the repo's install; its byproducts (a rewritten lockfile) are not committed
  unless the user says so.

Without orca:

```bash
git -C <repo> worktree add -b "feat/<STORY>" "<repo>/../<repo-name>-<STORY>" "origin/<root>"
git -C "<repo>/../<repo-name>-<STORY>" branch --unset-upstream 2>/dev/null
```

then run the repo's install command there.

**Sub-issue branches** are created from the story branch, inside the story worktree, when their
turn comes (Step 3). Before switching to another issue, the current one's work is committed — a
switch carries uncommitted changes along. Record 브랜치, 갈라진 곳, 기준 커밋, and the worktree for
every row.

Ask once whether to create every story worktree now (일괄) or each when its turn comes (순차), and
record it in the `워크트리:` header.

## D. Owners

- This session runs in the story worktree → it is the owner. Nothing to start.
- The row's `세션` column names a session that is still in the host's session list → that one.
- A session already runs there (the host's session list shows its working directory) → that one.
- Otherwise start one, by the rung Step 1 probed:
  1. `orca terminal create --worktree "path:<wt>" --title "<STORY>" --command "claude" --json`, then
     `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 120000`; find the new
     session in the host's session list and message it.
  2. Ask the user to open one (`cd <wt> && claude`), then message it.
  3. Print `cd <wt>` and the instruction text for the user to paste.

Write the session's name into the row's `세션` column as soon as it exists, and clear it when that
session is gone from the list. Re-deriving the worktree-to-session match from working directories on
every run is what makes two runs of the same command behave differently.

## E. Shared work

**스토리 공용** — triggered by a `**blocker**: 스토리 공용 — …` line or a `[공용 필요]` message. In the
story worktree: commit the current issue, switch to `feat/<STORY>`, build it, commit, switch back,
`git merge feat/<STORY>` — merge is fine below the root, the squash into the root hides it.

**메타 플랜 공용 (스토리 여러 개)** — its own top-level worktree and owner; PR to the root. A story
that needs the code before it lands takes it by cherry-pick onto its story branch, then its active
sub-issue merges the story branch. The tracker runs the cherry-pick — mechanical, no code written; a
conflict stops it.

**루트가 바뀌면** (공용 or a fix landed) — in each story worktree: switch to `feat/<STORY>`,
`git rebase origin/<root>`. Commits cherry-picked from 공용 come back empty and git drops them; a
conflict on 공용's files keeps the root's side (`git checkout --ours <file>` — during a rebase,
"ours" is the branch being rebased onto). Push with `--force-with-lease` if it was pushed, update
기준 커밋, then move every sub-issue branch with `git rebase --onto feat/<STORY> <old story tip> feat/<KEY>`.

**공유 컴포넌트 차이** — collect every reported difference into the meta-plan table and ask the user
once per new row: 보류, or 치명적? For 치명적: an `오류건` issue assigned to the user, a top-level
`fix/<KEY>` worktree from `origin/<root>` with its own owner, PR to the root; when it lands, rebase
the stories as above.

## F. Finishing an issue

When a row reaches `완료`:

1. Move the issue to `개발 완료`. Workflows refuse jumps — COMP goes `계획 → 개발예정 → 개발진행중 →
   개발 완료`, and `acli jira workitem transition --status` only takes a status reachable from the
   current one. Walk the path one step at a time (`--key <KEY> --status "<next>" --yes`), and record
   the path in the `지라 전환:` header the first time you learn it. The same applies to `개발진행중`
   when a row first reaches `구현`.
2. Comment from `${CLAUDE_SKILL_DIR}/templates/done-comment.template.md`:
   `acli jira workitem comment create --key <KEY> --body-file /tmp/tracker-<KEY>-done.txt`
3. Move its `구현 영향 없음` questions into the meta-plan's `## 남은 질문`.
4. Point the user at the PR — `/git-pr` cannot be called from a skill:

   ```
   COMP-408 완료 — 브랜치 `feat/COMP-408`
   PR: COMP-364 탭에서 `/git-pr --base feat/COMP-364`
   ```

5. Go on to the next sub-issue of the story (Step 3).

When every sub-issue of a story is `병합` into it, offer the 기획서 recheck (**G**) once, then rebase
the story onto `origin/<root>` and point the user at `/git-pr --base <root>` in the story worktree.
Every PR into the root is squash-merged.

When the whole tree is `병합`, report it and ask whether to remove the worktrees
(`orca worktree rm`). Deleting is the user's call.

## G. 기획서 다시 보기 — only when the user asks for it

The 기획서 is fetched once, in **A**, and not again while the work runs: a spec that moves under a
running implementation costs more than it saves. The one moment a change is worth catching is after a
story's sub-issues are all merged and before its PR opens. Ask there, once:

```
COMP-364 하위 이슈 {N}건 완료 — 기획서가 그동안 바뀌었는지 확인할까요?
```

Only on a yes:

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url>" \
  --output /tmp/tracker-source-new.md --metadata /tmp/tracker-source-new.json
diff -u "<repo>/docs/{name}/기획-snapshot.md" /tmp/tracker-source-new.md
```

No difference → one line saying so, and carry on. A difference → report it by story. The meta-plan
already maps 기획 sections to stories, so the diff can be read as "which issue is affected":

```
기획서가 바뀌었습니다 (스캔 시점 {날짜}).

| 바뀐 섹션 | 스토리 | 이슈 | 무엇이 |
| --- | --- | --- | --- |
| {섹션 제목} | 스토리 2 | COMP-408 | {추가·삭제·문구 변경 한 줄} |

PR을 열기 전에 반영할지 결정해 주세요.
```

Quote the changed 기획 text; never summarize it. A changed user-facing string is most of the reason
this step exists. Whether to fold the change in is the user's decision — a yes re-enters Step 3 as a
new or reopened issue, a no leaves the work as it is. Either way, once it is settled: overwrite the
snapshot with the fetched copy, update the `기획 스냅샷:` header, and let both ride along with the
story's next commit.

## RN apps

`/qa` drives a headless browser and cannot run a React Native app; `/implement` writes a
`## 기기 확인` checklist instead, and the user checks it. At most two worktrees can run on simulators
at once — Metro ports and bundle IDs give two lanes.

## Known hazards

- **Commit hooks** can add files (a bumped build number) or run long post-commit jobs. If
  `git status` fails right after a commit (`fatal: unable to read <hash>` — a hook rewrote the
  index), check the commit is intact with `git show --stat HEAD`, then rebuild the index with
  `git read-tree HEAD`. Ask the first time in a repo; afterwards follow what the user decided.
- **Jira ADF** rejects a code mark combined with any mark but a link. `md_to_adf.py` drops the others
  inside code spans; do not hand-edit its output.

## When the tracker stops

| 상황 | 왜 |
|---|---|
| 메타 플랜 작성 직후 | 범위를 잘못 가르면 뒤가 전부 틀린다 |
| 지라 이슈 목록 | 만드는 순간 팀 전체에 보인다 |
| 루트 (저장소마다 1회), 워크트리 배치 (1회) | 되돌리기 번거롭다 |
| 계획 검토, 작업 중 막힌 질문, 기기 확인, PR 열기 | 사람만 할 수 있다 |
| 새 공유 컴포넌트 차이 | 치명적인지는 사람이 판단한다 |
| 기획서가 바뀐 것을 발견 | 지금 반영할지는 사람이 정한다 |
| cherry-pick·rebase 충돌 | 추측으로 풀면 코드가 사라진다 |
| 파일과 문서가 설명 없이 어긋남 | 덮어쓰면 손실이 난다 |

## Rules

- **Run the next step; do not describe it** — a skill this session can run is run, not handed to the user to type
- **Keep going until a person has to decide** — a finished step, a report, an idle notice all restart Step 2
- **Stories are top-level worktrees** — `--no-parent`, wherever /tracker runs; sub-issues switch inside, unless the user asked for another layout
- **A new story worktree is checked for a 상위 워크트리 right after it is created** — `orca worktree list --json`, not a hope
- **One `[프론트]` sub-issue per story** — more only when the 기획서 separates the screens, and the section that separates them is named in 근거; the issue list is asked with the fixed template
- **The orchestration rung is probed and written down, never guessed** — every report opens with it, and a failure downgrades it out loud
- **Jira is read every run, not only written** — the files decide, Jira is walked forward to match, and the move goes in the report
- **The 기획서 is re-read only when the user says so** — offered once, after a story's sub-issues are merged
- **The meta-plan is versioned on the story branch** — never in `.git/info/exclude`
- **State comes from files** — checkboxes, `**blocker**` lines, `git log`, `gh pr list`; a reply is a hint to go look
- **`## 기록` carries only what the 작업 트리 표 and `git log` cannot** — a rebase that moved 기준 커밋, a cherry-pick, a 치명적 판단, a scope change. A status transition is never written down; the 상태 column already moved
- **Judgment is never deleted** — a decision that shaped one item lives as a `결정:` sub-bullet on that item in the owner's `tasks.md` and stays after the item is checked; only decisions spanning issues reach the meta-plan
- **The root is untouchable** — branch from `origin/<root>`, no upstream to it, no commit/push/force-push; take it in with rebase, land on it with squash
- **PRs go where the branch came from** — sub-issue → story, story / 공용 / 버그 → root
- **Blocker questions are asked where the work happens** — the tracker shows them, never relays them
- **Shared primitives are not edited** — collect the difference; only a user-approved 치명적 one gets a `fix/` branch
- **Promote on the spec's second caller** — same 문구 row or Figma node in two places; never on "looks reusable"
- **Quote the 기획서, never summarize it; never invent a user-facing string**
- **Jira is written only as authorized above** — create after approval, comment, walk transitions; never a story's description
- **Portable by default** — every question and report is plain conversation, and each rung in **D** works without the one above it
- Output documents and user communication are in Korean

## Communication Style

Write for a reader who has not implemented this feature and does not share your context: background
before conclusion, no unexplained internal term, one clear line instead of a paragraph they skip, no
filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what was intended.

Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to conversational output and to free-text prose inside `meta-plan.md` — `전체 범위`,
`하는 일`, gap reasons, `## 기록` lines. Tables, headers, links, and quoted 기획서 text keep their
normal format; quoted text is source material and is never rewritten to fit these rules.
