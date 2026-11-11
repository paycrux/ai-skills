# Feature documents — one PRD across several Jira stories

A PRD (기획서) that spans several Jira stories becomes several branches at once. The feature
document is the one place that says how the PRD was cut: PRD sections → stories → Jira sub-issues →
branches and worktrees → flow tasks. It replaces the removed `/tracker` meta-plan
(`docs/<name>/meta-plan.md`, still read as legacy). It only shows and records; it never sends work to
another session. Each worktree's session runs its own `/flow` task.

Contents: when · files · feature.json · draft and stop · snapshot · start · Jira · the page · after start

## When

Entry rule: a PRD plus several Jira story links → a feature document **draft**. One story, one
screen → a plain `/flow` task, no feature document.

## Files

```
<docs>/features/<id>/
  feature.json       the document (Claude writes it)
  prd.md             PRD snapshot — committed, never edited by hand
  issues/<row>.md    description of each sub-issue still to create (templates/dev-issue.template.md)
  index.html         feature page (generated, not committed)
```

`flow.py feature <docs> <id> --title "<한국어>" --root <root branch> [--prd <url>]` writes the skeleton.

## feature.json

```json
{
  "id": "gift", "title": "선물하기", "root": "main-rn0.83", "repo": "<original checkout, absolute>",
  "prd": [{"label": "선물하기 기획서", "url": "…", "snapshot": "prd.md", "lastEdited": "2026-09-16T05:42:00.000Z"}],
  "links": [{"label": "Figma 선물하기", "url": "…"}],
  "scope": ["<background sentence>", "<goal sentence>"],
  "jira": {"project": "COMP", "issueType": "[개발]", "titlePrefix": "[프론트]", "site": "https://<site>.atlassian.net", "path": [
    {"status": "계획"}, {"status": "담당자 확인 중"}, {"status": "작업 중", "mark": "start"},
    {"status": "[DEV] 개발 완료", "via": "개발계 배포 완료", "manual": true, "mark": "done"}]},
  "rows": [{
    "id": "gift-shop", "story": "COMP-358", "storyTitle": "[모바일오더] 선물하기",
    "title": "[프론트] 기프트샵·선물 결제", "sections": ["1-1 ~ 1-3"],
    "prd": "prd.md", "domain": "gifting", "domainTitle": "선물하기", "stages": "plan,screen,tasks",
    "figma": [{"label": "기프트샵", "url": "…"}], "issueBody": "issues/gift-shop.md",
    "approved": false
  }],
  "copy": [{"where": "<화면>", "when": "<무엇을 했을 때/어떤 상태일 때>",
            "kind": "<스낵바 · 토스트 · 인라인 메시지 · 확인 모달 · 툴팁 · placeholder · 빈 상태 문구 …>",
            "text": "“…”", "row": "<row>"}],
  "shared": [{"item", "usedBy": [], "evidence", "buildIn", "status"}],
  "componentDiffs": [{"component", "diff", "reportedBy", "decision"}],
  "questions": [{"row", "text"}],
  "log": [{"date", "text"}]
}
```

- **One row = one Jira sub-issue = one worktree = one branch `feat/<KEY>` = one flow task `<KEY>`.**
  Every story gets exactly one row; more only when the PRD itself separates the story into screens
  that ship independently — name that section in the row's `sections`. An existing `[개발]`
  sub-issue assigned to the user goes in `issue` and is reused.
- `sections` — PRD section numbers the row owns (`"2-1"`, `"2-4 ~ 2-7"`, `"1 ~ 3"`). The page also
  reads each task's `plan` quote sources, so a task that quotes a section owns it without editing
  this list.
- `prd` — the row's snapshot file, required when `prd[]` has more than one snapshot: PRD pages each
  number from 1, so a bare `"1-1"` matches several. One entry can override it with
  `"<snapshot>#1-1 ~ 1-3"`. A number found in several snapshots with no `prd` gets no dot; the
  matrix lists it in amber instead.
- `start` fills `issue`, `worktree`, `branch`, `base`, `task`, and the document's `home`. Never write
  progress, stage or checklist counts here — the page reads them from each row's task.
- `jira.titlePrefix` — what the team puts in front of a sub-issue title (`[프론트]`, `[FE]`, `[앱]`, or
  `""` for none). Learned once per feature, never assumed: read the titles of the sub-issues already
  under the stories (step 2 of § Draft and stop) and take the prefix they share; with none to read or
  no shared prefix, ask the user once. Every new row's `title` starts with it, and `check` fails an
  approved row while it is unset. The flow task title is the row title without it.
- `jira.path` — the issue workflow, learned once (§ Jira). `mark: "start"` is where implementation
  begins, `mark: "done"` where flow stops. `manual: true` marks a transition with a precondition
  that the files cannot show (a dev deploy); flow never takes it.
- `copy` — every snackbar, modal, button and error string, verbatim from the PRD. Missing copy is a
  `questions` entry, never invented. A bare list of strings says nothing about when each appears, so
  every entry carries the screen, the trigger and the form:
  - `where` — the screen. The same string on several screens is one entry per screen; never dedupe.
  - `when` — the user's action or state, as a sentence: "[로그인]을 눌렀는데 비활성 처리된 구성원일
    때", "입력한 값이 있는데 [취소]·뒤로가기로 나가려 할 때". A placeholder such as N is named here
    ("(N = 겹친 건수)"). Copy the PRD gives only as "~와 동일" names its source here too.
  - `kind` — the form: 스낵바 · 토스트 · 인라인 메시지 · 확인 모달 · 툴팁 · placeholder · 빈 상태
    문구 …. A modal names its buttons: "확인 모달 (2줄) · 버튼 [취소] [폐점 처리]".
  - `text` — the PRD string in “…”. A multi-line modal is one entry, lines separated as “…” / “…”.
  - The page shows 화면 · 언제 · 형태 · 문구 · 작업; a document with no `when`/`kind` at all keeps
    the old 위치 · 문구 · 작업 table. Each `issues/<row>.md` repeats its rows' entries in the same
    columns (`templates/dev-issue.template.md`).
- `shared` — only when the PRD shows the same element in two or more rows (same copy row, same Figma
  node). Across stories it gets its own row and branch, PR to the root; app-wide primitives are not
  edited — their differences go in `componentDiffs`, and the user decides 보류 or 치명적.
- `log` — only what the rows and `git log` cannot hold: a rebase that moved a base, a cherry-pick, a
  치명적 judgment, a scope change, whether a PRD change was folded in. Never a status change.
- A row from before this change keeps its old plan: `"legacy": "docs/gift/plans/tasks.html"` and
  `sections`; the page shows it as 레거시.

## Draft and stop

1. **PRD** — fetch the snapshot (§ Snapshot), list its headings, read only what you need to cut it.
2. **Stories and existing sub-issues** —
   `acli jira workitem view <STORY> --fields summary,issuetype,status,parent --json` and
   `acli jira workitem search --jql "parent = <STORY>" --fields key,summary,assignee,status --json`.
   The sub-issue titles found here give `jira.titlePrefix`.
3. **Design, shallow only** — `get_metadata` one level down per frame; never `get_design_context`
   here. Record frame names and node IDs in each row's `figma`.
4. **Map** sections → stories → rows. Write one `issues/<row>.md` per new row from
   `${CLAUDE_SKILL_DIR}/templates/dev-issue.template.md` — PRD text quoted, never summarized.
5. `flow.py build <docs>`, `flow.py open <docs>/features/<id>/index.html`, and **stop**. The page
   marks every 주인 없는 섹션 and every section a task cites that the snapshot lacks.

```
기능 문서 초안을 썼어요. 스토리 2개, 하위 이슈 3개(새로 만들 것 2개)예요. 제목 접두어는 기존 하위 이슈를 따라 [프론트]로 했어요.
주인 없는 기획 섹션 1개가 노랗게 표시돼 있어요. 열린 페이지를 보고 고칠 곳을 알려 주세요.
괜찮으면 "진행해" — 지라 이슈 · 워크트리 · 브랜치 · flow 작업을 만들어요. 이슈는 만드는 즉시 팀에 보여요.
```

The only answers that change the rows are 추가 · 삭제 · 제목 · 분할. On approval run, **in the same
turn**, `flow.py start <docs>/features/<id>/feature.json --approve`.

**Root** — the branch other developers share. Reuse the `root` of another feature document in this
repository; otherwise ask once. Never derive it from a rule like "develop, else the default branch".

## Snapshot

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url>" \
  --output "<docs>/features/<id>/prd.md" --metadata /tmp/flow-prd-meta.json --check-auth
```

- Commit `prd.md` with the feature document. It is the only record of what the PRD said when the
  scope was cut; editing it by hand makes the later diff lie.
- Copy `last_edited_time` from the metadata into `prd[].lastEdited`. A PRD split across sub-pages
  gets one `prd` entry and one snapshot file per page — editing a child page does not move the
  parent's time.
- The PRD is fetched again **only when the user asks**. Then fetch to a temp file, `diff -u` against
  `prd.md`, and report changed sections by row, quoting the changed text. Whether to fold the change
  in is the user's call; once settled, overwrite `prd.md`, update `lastEdited`, and add a `log` line.

## Start

`flow.py start <feature.json> [--row KEY]... [--approve] [--dry-run]` makes, for every approved row,
in order, saving after each step so a rerun continues where a failure stopped:

1. **Jira** — a sub-issue titled with the row's `title` under `story` (`acli`, description converted by
   `_shared/jira/md_to_adf.py`, assignee `@me`); an existing sub-issue with the same summary is reused.
2. **Worktree** — `git fetch origin <root>`, then an orca **top-level** worktree
   (`--no-parent`, base `origin/<root>`, branch `feat/<KEY>`), then `orca worktree list --json` to
   confirm it has no parent worktree (`orca worktree set --no-parent` once, else stop). Without orca:
   `git worktree add` beside the repository.
3. **Branch** — renamed to `feat/<KEY>` if needed, upstream removed so a bare `git push` can never
   reach the root; `base` records the starting commit.
4. **Task** — `docs/<domain>/tasks/<KEY>.json` in the new worktree with `branch` set exactly, the
   PRD · Figma · Jira links, `feature` pointing back at this document, and the row's `stages`. A
   domain the root does not have yet is created from `domainTitle`.

The first time, the feature folder moves to the first row's worktree (`home`) and is committed there
with that branch's next commit; the other worktrees read it by absolute path. It makes no judgment:
anything not approved in the document is not created.

The root is never committed to, pushed, or force-pushed. orca's setup hook may rewrite a lockfile;
that byproduct is not committed unless the user says so.

## Jira

**Learn the path once.** `acli` cannot list transitions. Read them with the Atlassian MCP
`getTransitionsForJiraIssue` (`includeUnavailableTransitions: true`), and write `jira.path` with the
transition names in `via`. A transition whose name or screen carries a precondition the files cannot
show (`[DEV] 개발 완료` reached by "개발계 배포 완료") is `manual: true`.

| When | Command | Does |
|---|---|---|
| `tasks` stage goes `now` (구현 시작) | `flow.py jira <task.json> start` | walks one transition at a time to `mark: "start"` |
| 05 완료, after `/code-review` | `flow.py jira <task.json> done` | posts the done comment (`templates/done-comment.template.md`, filled from the task, `git log`, and `questions`), then walks toward `mark: "done"` |

A `manual` step is never taken: the row's `jira.todo` gets "사람이 옮길 것" and the feature page shows
it in red. A refused transition stops the walk — re-read the transitions and fix `jira.path`. A task
without a feature document can carry `jira.path` itself.

## The page

`docs/features/<id>/index.html`, linked from every task page's header (기능 …) and the nav's 기능
group:

- 작업 — one line per row: issue, story, branch · worktree, each stage's status, checklist count,
  Jira status, and below it what a person has to do next (question, plan review, device check, a
  Jira move by hand). All read from the row's task: this checkout, else the row's worktree, else
  `git show <branch>:…`.
- 기획 섹션 × 작업 — a dot where a row owns a section, grouped by snapshot when there are several.
  주인 없는 섹션, 스냅샷에 없는 섹션 and a number several snapshots share are amber rows.
- Table headers stay pinned while their table scrolls.
- 사용자 노출 문구, 범위 간 공유물, 공유 컴포넌트 차이, 남은 질문, 기록, 지라 전환.

## After start

Each worktree is worked in its own session: open the worktree, and the SessionStart hook
(`flow.py current`) names the task on that branch. Blocker questions are asked in that tab; a
decision that shaped one item stays a `결정` row in that task. Only cross-row matters reach the
feature document. Commit before switching branches; PRs go to the root, squash-merged.
