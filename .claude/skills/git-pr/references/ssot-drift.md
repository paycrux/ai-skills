# SSOT drift — when the code gets ahead of the PRD or Figma

The PRD (Notion) and Figma are the SSOT for what a screen shows and does. A hotfix, an operations
fix, or a small bug fix can change visible behavior before anyone updates them. Nobody in 기획 ·
디자인 reads commits or flow documents, so without a note where they look, the SSOT goes stale in
silence. This step leaves that note on the original Jira issue: a label they can filter on and a
comment saying what differs. Whoever updates the SSOT removes the label — that closes it.

Read this at **SSOT drift** in the PR phase.

## Contents

- [1. Judge](#1-judge)
- [2. Confirm in the draft](#2-confirm-in-the-draft)
- [3. Post to Jira](#3-post-to-jira)
- [Closing a drift](#closing-a-drift)

## 1. Judge

Go through the diff you already read for the draft. A change is **drift** when all of these hold:

1. **A user can see it** — copy, layout, an element shown or hidden, a condition that changes what
   shows, navigation, timing, motion. Refactors, types, logging, and tests are never drift.
2. **It departs from what the PRD or Figma says, or adds what they do not say.** Bringing the code
   back in line with the spec is a fix, not drift. Sources to compare against, in order: the
   `FLOW_TASK`'s PRD snapshot and SOT map rows, the Jira issue's description and its PRD/Figma
   links (`acli jira workitem view {KEY} --fields description --json`), then the code's own history
   (`git log -p` on the changed lines). When none of them tells you what the spec says, list the
   change as a candidate and say the spec was not checked — the user drops it at confirmation.
3. **It is not code-owned.** Skip a property declared in a domain's `screens.json` `codeOwned`
   whose `at` names the changed file (`grep -l '"<changed file>' docs/*/screens.json`). Its `file:line`
   still has to match the property the diff touches; a changed file that merely appears there is not
   enough.
4. **It is not already carried by a flow task.** When `FLOW_TASK` is set, the PRD requests its 05 완료
   block lists are drift too — include them, so they reach Jira as well as `## 남은 요청`.

Write each drift as one line a planner or designer can act on without the code: the screen, what
the SSOT says, what the app does now, and why it changed.

```
- 선물함 · 카드 목록: 기획서는 만료된 카드를 숨김 → 지금은 회색으로 맨 아래에 보여줌 (운영 문의: 만료 카드가 사라졌다는 신고)
```

No drift → say so in one line with the draft and skip the rest.

## 2. Confirm in the draft

The Jira key is the resolved `ISSUE_NO` when it is a Jira key (`[A-Z][A-Z0-9]+-\d+`). Show the drift
lines with the PR draft — in the conversation, or above the `<!-- ↓↓↓ PR 본문 시작 ↓↓↓ -->` marker in
preview-file mode — never in the PR body. Then ask:

- prompt: `"화면 동작이 기획서·Figma와 달라진 부분이 있어요. PR을 만든 뒤 {KEY}에 ssot-drift 라벨과 아래 댓글을 남길까요?"`
- options: `["남기기 — 라벨 + 댓글", "고쳐서 남기기 — 항목을 빼거나 고친 뒤 다시 확인", "남기지 않기"]`

No Jira key → do not ask. Show the lines and say there is no Jira issue to post them to, so the user
can pass them on by hand.

## 3. Post to Jira

Only after the PR is created, and only with `남기기`. Read the labels first so the edit keeps them:

```bash
acli jira workitem view {KEY} --fields labels --json
acli jira workitem edit --key {KEY} --labels "{existing labels},ssot-drift" --yes
acli jira workitem comment create --key {KEY} --body-file {REPO_ROOT}/.ssot-drift.tmp.txt
```

The comment, as plain text:

```
[SSOT 불일치] 코드가 기획서·Figma보다 앞서 바뀌었어요.

- {drift line}
- {drift line}

PR: {PR URL}
기획서·Figma를 갱신한 뒤 이 이슈의 ssot-drift 라벨을 떼 주세요.
```

Delete `.ssot-drift.tmp.txt` afterwards and never commit it. A failed `acli` call does not undo the
PR: report the error in Korean and leave the comment text in the conversation so it can be posted
by hand.

## Closing a drift

The open list is the JQL `labels = ssot-drift` — save it as a Jira filter for 기획 · 디자인. When the
PRD or Figma is updated, the person who updated it removes the label:

```bash
acli jira workitem edit --key {KEY} --remove-labels ssot-drift --yes
```
