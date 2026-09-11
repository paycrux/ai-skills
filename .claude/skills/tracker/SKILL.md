---
name: tracker
description: "Control session for a feature that spans several Jira stories. Given Notion + Jira story + Figma links once, it writes a meta-plan, creates a [프론트] dev sub-issue per story, opens a worktree and a Claude session per issue, and hands the work over. On every later run it reads every worktree's files, collects the state, and says what happens next. Use when the user runs /tracker, or hands over planning links for work across several stories."
argument-hint: "[notion url] [jira story links] [figma links] — or nothing, to continue"
---

# /tracker — 관제 세션

A feature that spans several Jira stories is several branches at once. Git keeps those branches
apart until they merge, so a worktree cannot see the meta-plan or its siblings' progress through
git. But every worktree is a folder on the same disk: any session can read any worktree's
`tasks.md` and `git log` by absolute path. This skill is built on that.

The tracker session is the control tower. It writes the meta-plan, creates the Jira issues, the
branches and the worktrees, starts a Claude session in each worktree, and reads their files to know
where everything stands. The work itself — planning, implementing, committing, asking the user
about blockers — happens in the worktree sessions, each in its own tab.

```
/tracker <노션> <지라 스토리들> <피그마>   ← 처음 한 번
/tracker                                   ← 그다음부터 계속 이것만
```

## Who does what

| | tracker session | worktree session |
|---|---|---|
| 위치 | 원래 체크아웃 (저장소의 main worktree) | 자기 워크트리 |
| 하는 일 | 메타 플랜, 지라, 브랜치·워크트리, 세션 띄우기, 상태 읽기, 결과 보고 받기 | `/task-plan`, 계획 검토, `/implement`, 막힌 질문, 커밋, 기기 확인 체크리스트 |
| 쓰는 파일 | 메타 플랜, 지라 | 자기 `tasks.md`·`spec.md`·코드 |
| 하지 않는 일 | 워크트리 드나들기, 코드 쓰기, 워크트리의 막힌 질문 대신 묻기 | 메타 플랜 쓰기, 루트 건드리기, 공유 컴포넌트 고치기 |

**Blocker questions stay in the worktree tab that hit them.** The tracker only receives results.
It learns about a blocker by reading `**blocker**` lines in `tasks.md`, and shows them in its
status table; it never relays the question.

**Completion is decided from files, never from a session's reply.** A report that says "done" is
checked against the checkboxes and `git log` before anything is recorded.

## What running /tracker authorizes

Running this skill is the user's standing permission for these, and only these:

- A worktree session commits its own work as soon as implementation finishes
- `git push --force-with-lease` on a branch listed in this meta-plan's 작업 트리, after a rebase
- Jira: create issues once the list is approved; comment on them; move them to `개발진행중` / `개발 완료`

Never, under any flow: commit, push, or force-push to the root; touch a branch that is not in the
작업 트리; edit a story's description (backend, 기획, and design share the story).

## Step 1: Find the work

Always work from the original checkout — the first entry of `git worktree list --porcelain`. If
this session was started inside a worktree, resolve that path and use it by absolute path. Never
`EnterWorktree` from the tracker session: a second `orca worktree create` from inside a worktree is
refused by the isolation guard.

- **Arguments contain links** → go to **A**.
- **No arguments** → read `<repo>/docs/*/meta-plan.md`. Take the one whose 작업 트리 still has a row
  that is not `병합`. Several → list them and ask. None → say so and stop.

## Step 2: Read the state — every run

1. `git -C <repo> worktree list --porcelain` → branch → worktree path.
2. For every 작업 트리 row that has a worktree:
   - **Plan** — the `docs/*/plans/tasks.md` whose `> 이슈:` header is this row's key. A worktree
     carries every plan that existed on its base, so match by key, never by existence.
   - **Progress** — checked / total items under the `## Phase` headings; every line containing
     `**blocker**`; the `## 기기 확인` checklist, if present.
   - **Commits** — `git -C <wt> log --oneline <기준 커밋>..HEAD`, and
     `git -C <wt> status --porcelain` for anything uncommitted.
   - **PR** — `gh pr list --head <branch> --state all --json number,state,baseRefName`.
3. Derive the state:

   | 관측 | 상태 |
   |---|---|
   | 워크트리 없음 | 대기 |
   | `tasks.md` 있음, 체크 0 | 계획 |
   | 체크 1개 이상, 남은 항목 있음 | 구현 |
   | Phase 전부 체크 + 커밋 있음 + `## 기기 확인` 남음 | 확인 |
   | `## 기기 확인` 전부 체크 (웹: `qa-report.md`에 미해결 버그 없음) | 완료 |
   | PR 열림 | PR |
   | PR 병합됨 | 병합 |

   Blocker lines do not change the state; they are shown next to it.

4. **Files win.** When the meta-plan disagrees with the files, correct the meta-plan and carry on
   without comment. When the disagreement has no explanation you can verify — a branch gone, a
   worktree missing with work unaccounted for — stop and report it instead of guessing.
5. Act on what changed since the last run — **F** for finished issues, **E** for shared-work
   triggers — then report:

   ```
   | 이슈 | 상태 | 커밋 | blocker | 다음 |
   | --- | --- | --- | --- | --- |
   | COMP-401 [프론트] 로그인 화면 | 구현 12/19 | 3 | 1 — 탈퇴 에러 코드 | COMP-401 탭에서 답변 대기 |
   | COMP-402 [프론트] 회원가입 약관 | 확인 | 5 | - | 기기 확인 대기 |

   지금 할 일: {tracker가 방금 한 것} / {사용자가 할 것 — 탭 이름·명령까지}
   ```

## A. Write the meta-plan

One 기획서, one meta-plan. Given several, ask which to start with. Derive `{name}` — a kebab-case
English slug from the Notion title — and confirm it.

**기획서**

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url>" \
  --output /tmp/tracker-source.md --metadata /tmp/tracker-source.json --check-auth
```

The script replaces Notion's signed image URLs with a placeholder; they are ~1.5 KB each and
expire within the hour. Split on `## ` headings ignoring leading whitespace — a Notion column layout
indents them.

**스토리와 기존 하위 이슈**

```bash
acli jira workitem view <STORY> --fields summary,issuetype,status,parent,description --json
acli jira workitem search --jql "parent = <STORY>" --fields key,summary,issuetype,assignee,status --json
```

An existing `[개발]` sub-issue assigned to the user is reused. Anyone else's is left alone.

**디자인 — shallow only.** `get_metadata` frame by frame: a section node can exceed 100K characters,
so go one level down instead of reading the section. `get_screenshot` only when a frame name is
useless (`Frame 427`). Never `get_design_context` — dimensions and colors are read from the
original at implementation time. Record frame names and IDs, **modal and state frames included**:
the implementer finds its design nowhere else.

**스토리 = 범위.** Map 기획 sections → stories → frames. The 기획서 often states its own split (a
callout listing its sections); read that before inferring one. Report both gaps — a 기획 section no
story takes, a story no 기획 section covers.

**사용자 노출 문구** — every snackbar, modal, button, and error string, verbatim, in a table per
story, with the dev issue that renders it. Never paraphrase one; never invent one — a missing string
goes on the story's `미정` line.

**개발 이슈** — every story gets at least one `[프론트] <화면·기능>` sub-issue, even a small one: the
story is shared with backend, 기획, and design, and the sub-issue is the frontend's own. Split a
large story by independent screen or feature.

**범위 간 공유물** — promote only when the 기획서 shows the same element in two or more places: the
same 문구 row, the same Figma node. That counts as the second caller (global rule exception). "Looks
reusable" does not.

| 쓰는 곳 | 단계 | 어디서 만드나 |
|---|---|---|
| 스토리 여러 개 | 메타 플랜 | 공용 `[개발]` 이슈의 독립 브랜치 — 루트에서 따서 루트로 PR |
| 한 스토리의 개발 이슈 여러 개 | 스토리 | 그 스토리의 부모 워크트리 |
| 앱 전체 (`components/ui/*`, `domain/common` 등) | 전역 | 고치지 않는다 — **E**의 공유 컴포넌트 차이 |

**Write** `<repo>/docs/{name}/meta-plan.md` from `${CLAUDE_SKILL_DIR}/templates/meta-plan.template.md`,
in Korean, and keep it out of every commit in every worktree:

```bash
echo "docs/{name}/meta-plan.md" >> "$(git -C <repo> rev-parse --git-common-dir)/info/exclude"
```

**Root** — the branch other developers share. Reuse the `루트:` of another meta-plan in this repo;
otherwise ask once. Do not derive it from a rule like "develop, else the default branch": the real
base is often a release line the default branch lags behind.

Then **stop**. Nothing is in Jira yet.

```
메타 플랜을 작성했습니다.

- 문서: `{repo}/docs/{name}/meta-plan.md`
- 스토리 {N}개, 개발 이슈 {M}개 (새로 만들 것 {K}개), 공용 {J}개
- 어디에도 안 붙은 기획: {N}건 / 기획이 없는 스토리: {N}건 / 미정: {N}건   ← 있을 때만

검토하시고 고칠 부분을 알려주세요. 괜찮으면 만들 지라 이슈 목록을 보여드립니다.
```

## B. Create the Jira issues

Show the list and **stop for approval** — an issue is visible to the whole team the moment it
exists:

```
| 만들 이슈 | 부모 | 제목 | 담당 |
| --- | --- | --- | --- |
| 새로 | COMP-344 | [프론트] 로그인 화면 | 나 |
| 재사용 COMP-367 | COMP-356 | [모바일오더] 카드등록 | 나 |
```

For each approved issue, re-check that the parent has no sub-issue with the same summary (a re-run
must not create twins), then:

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/jira/md_to_adf.py" /tmp/tracker-<KEY-or-slug>.md -o /tmp/tracker-<KEY-or-slug>.adf.json
acli jira workitem create --project <PROJECT> --type "[개발]" --parent <STORY> \
  --summary "[프론트] <화면·기능>" --assignee @me \
  --description-file /tmp/tracker-<KEY-or-slug>.adf.json --json
```

The markdown comes from `${CLAUDE_SKILL_DIR}/templates/dev-issue.template.md` — a `## 기획 리뷰`
section with this issue's 기획 발췌, 문구, frames, and open points. The converter never emits
Jira task-list nodes; a `- [ ]` line becomes a plain bullet. A 공용 issue is the same, parented to
the story that uses it first and titled `[프론트] <무엇> 공용`. Sub-issue type names differ per
project — read them from `acli jira project view --key <PROJECT> --json` rather than assuming.

Write every key into the 작업 트리.

## C. Branches and worktrees

Ask the worktree policy once, then record it in the header:

> 워크트리를 어떻게 만들까요?
> - 일괄 — 지금 다 만듭니다. 세션도 한꺼번에 띄워 탭을 오가며 진행합니다.
> - 순차 — 차례가 된 이슈만 만듭니다.

**The tree:**

```
<root>
├─ feat/<공용 키>     루트에서. PR → 루트 (squash)
├─ feat/<스토리 키>   루트에서. 브랜치만 — 워크트리는 스토리 작업이 생길 때
│   └─ feat/<하위 키> 스토리 브랜치에서. PR → 스토리 브랜치
└─ fix/<버그 키>      루트에서. PR → 루트 (squash)
```

A story branch is just `git -C <repo> branch feat/<STORY> <root>`. Its worktree appears only when
story-level work does: story 공용, a cherry-pick from 공용, a rebase onto the root, the story PR.

**Making a worktree — orca first:**

```bash
orca worktree create --name "<KEY>" --repo "path:<repo>" --base-branch "<갈라진 곳>" --json
git -C "<path>" branch -m "$(git -C "<path>" branch --show-current)" "feat/<KEY>"
```

orca has no branch-name option and prefixes the GitHub login (`AeiYo/COMP-344`); the rename gives
the `feat/<KEY>` the team uses. The first time in a repo, confirm with `orca worktree list --json`
that orca still lists the path under the new branch, and write the result into `## 기록`.
`--repo` takes the original checkout's absolute path — `git rev-parse --show-toplevel` run inside a
worktree returns that worktree instead.

Without orca:

```bash
git -C <repo> worktree add -b "feat/<KEY>" "<repo>/../<repo-name>-<KEY>" "<갈라진 곳>"
```

then run the repo's install command there (from its lockfile) before handing it over — orca's setup
hook does this for you, plain git does not.

Record 브랜치, 갈라진 곳, 기준 커밋 (`git rev-parse <갈라진 곳>` at creation), and the path.

## D. Hand an issue to a worktree session

Use the best rung the environment has:

1. **orca and session messaging** — start Claude in the worktree, wait for it, then send the kickoff:

   ```bash
   orca terminal create --worktree "path:<wt>" --title "<KEY>" --command "claude" --json
   orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 120000
   ```

   Find the new session in the host's session list (its name comes from the worktree folder) and
   send the kickoff as a message. If it cannot be found, fall to rung 3 for this issue.
2. **Session messaging only** — ask the user to open a session there (`cd <wt> && claude`), then
   find it and message it.
3. **Neither** — print, per issue, `cd <wt>` and the kickoff text to paste.

The kickoff comes from `${CLAUDE_SKILL_DIR}/templates/kickoff.template.md`: meta-plan path, issue,
branch and origin, the root warning, and the order — `/task-plan` → review in that tab →
`/implement` → blockers asked in that tab → commit → 기기 확인 checklist → result report to this
session. One message covers the whole run; the tracker does not drip instructions.

When a row first reaches `구현`, move the issue: `acli jira workitem transition --key <KEY> --status
"개발진행중" --yes`. Status names are the project's own — check the ones its `[개발]` issues
actually use. If the workflow refuses, report it and continue.

## E. Shared work

**메타 플랜 단계 (공용 이슈)** — hand it over first; stories do not wait for it. A story that needs
the code before 공용 lands in the root takes it by cherry-pick into its story branch (creating the
story worktree for that), and its children take it from the story branch by merge. The tracker runs
the cherry-pick itself — it is mechanical, no code is written. A conflict stops it; report.

When 공용 squash-merges into the root, rebase each story branch onto the root in its story worktree.
Commits cherry-picked from 공용 come back empty and git drops them. If 공용 changed in review and the
rebase conflicts on its files, keep the root's side (`git checkout --ours <file>` — during a rebase,
"ours" is the branch being rebased onto). Push with `--force-with-lease` if the branch was pushed,
update 기준 커밋, then tell each child session to move with
`git rebase --onto feat/<STORY> <old story tip> feat/<KEY>` — without it, the pre-rebase story
commits ride the child's PR back into the story.

**스토리 단계** — triggered by a `**blocker**: 스토리 공용 — …` line in a child's `tasks.md`, or a
`[공용 필요]` message. Create the story worktree if it is missing, start a session there (**D**), and
send: what to build, which children wait on it, and "커밋 후 결과 보고". Once it is committed, tell
the waiting children to `git merge feat/<STORY>` — merge is fine below the root, the squash into the
root hides it.

**공유 컴포넌트 차이** — collect every difference sessions report into the meta-plan table. For
each new row, ask the user once: 보류, or 치명적? Leave 보류 rows alone. For 치명적: create an
`오류건` issue assigned to the user, a `fix/<KEY>` worktree from the root, and a session for it; its
PR goes to the root. When it merges, every story branch rebases onto the root as above.

## F. Finishing an issue

When a row reaches `완료`:

1. `acli jira workitem transition --key <KEY> --status "개발 완료" --yes`
2. Comment from `${CLAUDE_SKILL_DIR}/templates/done-comment.template.md` — 구현, commits, 미결:
   `acli jira workitem comment create --key <KEY> --body-file /tmp/tracker-<KEY>-done.txt`
3. Move its `구현 영향 없음` questions into the meta-plan's `## 남은 질문`.
4. Tell the user to open the PR — `/git-pr` cannot be called from a skill:

   ```
   COMP-401 완료 — 브랜치 `feat/COMP-401`
   PR: `{wt}` 탭에서 `/git-pr --base feat/COMP-344`
   ```

When every child of a story is `병합` into it, rebase the story onto the root in its story worktree,
then point the user at `/git-pr --base <root>` there. Every PR into the root is squash-merged.

When the whole tree is `병합`, report it and ask two things: commit the meta-plan into the repo or
leave it local, and remove the worktrees (`orca worktree rm`) or keep them. Deleting is the user's
call.

## RN apps

A React Native app cannot be driven by `/qa`; `/implement` writes a `## 기기 확인` checklist
instead, and the user checks it. At most two worktrees can run on simulators at once — Metro ports
and bundle IDs give two lanes. When more than two rows are in `확인`, say which two to run now.
Web projects use `/qa`.

## When the tracker stops

| 상황 | 왜 |
|---|---|
| 메타 플랜 작성 직후 | 범위를 잘못 가르면 뒤가 전부 틀린다 |
| 지라 이슈 목록 | 만드는 순간 팀 전체에 보인다 |
| 루트 (저장소마다 1회), 워크트리 정책 (1회) | 되돌리기 번거롭다 |
| 새 공유 컴포넌트 차이 | 치명적인지는 사람이 판단한다 |
| cherry-pick·rebase 충돌 | 추측으로 풀면 코드가 사라진다 |
| 파일과 문서가 설명 없이 어긋남 | 덮어쓰면 손실이 난다 |

Plan review and blocker questions are not on this list: they happen in the worktree tabs.

## Rules

- **The tracker is the only writer of the meta-plan** — sessions read it, people read it, nobody else writes it
- **State comes from files** — checkboxes, `**blocker**` lines, `git log`, `gh pr list`; a reply is a hint to go look
- **The root is untouchable** — no commit, push, or force-push; take it in with rebase, land on it with squash
- **PRs go where the branch came from** — child → story, story / 공용 / 버그 → root
- **Blocker questions stay in the tab that hit them** — the tracker shows them, never relays them
- **Shared primitives are not edited** — collect the difference; only a user-approved 치명적 one gets a `fix/` branch
- **Promote on the spec's second caller** — same 문구 row or Figma node in two places; never on "looks reusable"
- **Quote the 기획서, never summarize it; never invent a user-facing string**
- **Design is read shallowly here** — frame names and IDs only; `get_design_context` belongs to implementation
- **Jira is written only as authorized above** — create after approval, comment, two transitions; never a story's description
- **Portable by default** — every question and report is plain conversation, and each environment rung in **D** works without the one above it
- Output documents and user communication are in Korean

## Communication Style

Write for a reader who has not implemented this feature and does not share your context: background
before conclusion, no unexplained internal term, one clear line instead of a paragraph they skip, no
filler (전반적으로, ~등을 개선, 안정성 향상), and what actually is rather than what was intended.

Full rules: `${CLAUDE_SKILL_DIR}/../../rules/writing.md`.

This applies to conversational output and to free-text prose inside `meta-plan.md` — `전체 범위`,
`하는 일`, gap reasons, `## 기록` lines. Tables, headers, links, and quoted 기획서 text keep their
normal format; quoted text is source material and is never rewritten to fit these rules.
