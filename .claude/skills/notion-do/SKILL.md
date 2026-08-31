---
name: notion-do
description: "Read a Notion link via notion-cli and then do whatever the user asks with it — summarize, extract, answer questions, convert, draft, translate, build a checklist, and more. Use when a Notion URL or page ID is present in the chat and the user wants an action performed on that document."
argument-hint: "[notion-url-or-page-id] [what to do]"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit
---

# /notion-do — Read a Notion doc and act on it

Fetch a Notion document with `notion-cli`, explore it as needed, then perform the
action the user requested. Unlike a fixed summarizer, the action is open-ended:
summarize, extract fields, answer a question, convert to another format, draft a
follow-up, translate, or build a checklist — whatever the user asks.

## Argument Parsing

Split the input into two parts:

- **TARGET** — the Notion URL or page ID.
- **INTENT** — the action the user wants (everything that is not the URL/ID).

Rules:

- `/notion-do <notion-url-or-page-id> <intent>` — fetch the target and carry out the intent.
- If no URL/ID is in `$ARGUMENTS`, use the most recent Notion link in the conversation.
- If no explicit intent is given, default to a structured summary and offer next actions.
- Never pass the intent text (e.g. "summarize", "extract owners", "번역") to the CLI.

## Execution

### Step 1: Confirm access

Verify `notion-cli` is available and, if auth state is uncertain, check connectivity.

```bash
notion-cli whoami
```

If this fails, tell the user that authentication or page-share permission is required,
and include the failing command plus a short stderr excerpt.

### Step 2: Fetch the document

Use the bundled script to fetch the page as markdown. It extracts the page ID from a
URL, runs an auth check, and writes the body to a file so long documents are not pasted
into the conversation.

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "$TARGET" --output /tmp/notion-page.md --check-auth
```

Explore `/tmp/notion-page.md` with `Read`, `Grep`, or `rg` instead of dumping the full
source to the user.

> `fetch_notion_markdown.py`는 `create-prd`와 공유하는 스크립트라 `skills/_shared/notion/`에 있습니다.
> 경로가 없으면 설치가 불완전한 것이니 `ai-skills update`로 재설치하도록 안내하세요.

### Step 3: Understand the document

Identify title, purpose, section structure, tables, decisions, requirements, owners,
dates, risks, open questions, and action items — enough to satisfy the INTENT.

### Step 4: Gather more only if the intent needs it

Fetch metadata or child blocks, or follow one level of linked Notion pages, **only when
the intent requires it** (e.g. "include sub-pages", "list every linked doc", "who owns each item").

```bash
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "$TARGET" \
  --metadata /tmp/notion-page.json --children /tmp/notion-children.json --output /tmp/notion-page.md
notion-cli search --query "<title-or-keyword>" --limit 10 --json
```

Do not recursively crawl external links or unrelated databases without the user asking.

### Step 5: Perform the action

Carry out the INTENT against the fetched content. Common shapes:

| Intent | Output |
|---|---|
| Summarize / "무슨 내용이야" | Structured summary in the user's language |
| Extract (owners, dates, decisions, action items) | A focused list or table of just those fields |
| Answer a question | A direct answer grounded in the doc, quoting the relevant part |
| Convert (to PRD, checklist, table, tasks) | The requested format, written to a file if the user wants one |
| Translate / rewrite | The transformed text |
| Compare across pages | A side-by-side of the pages that were read |

If the action writes files (e.g. converting to a doc), confirm the output path before
creating anything outside the current directory or `/tmp`.

## Rules

- Prefer `notion-cli` over a browser for private Notion content.
- Answer in the user's language; Korean requests get Korean answers.
- Distinguish pages that were read from pages that failed to load in the final answer.
- Do not invent owners, deadlines, or dates — if the source omits them, say "not specified".
- If fulfilling the intent would require crawling many pages, confirm scope before proceeding.
- On failure, include the command run and a short stderr excerpt.
