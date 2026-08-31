---
name: create-prd
description: "Split a large markdown document into per-section files under docs/<name>/prd/ and generate an overview file with links. Accepts a local markdown path OR a Notion URL/page ID (fetched via notion-cli)."
argument-hint: "[markdown file path OR notion url/page id]"
allowed-tools: Bash, Read, Write, Grep, Glob
---

# Split Document

Target: $ARGUMENTS

The target may be a **local markdown file** or a **Notion URL / page ID**. Resolve it to a
local markdown file in Step 0, then follow the split steps.

## Steps

**Follow the order below exactly.**

### Step 0: Resolve the Source (local file vs. Notion)

Decide what the target is:

- If `$ARGUMENTS` is empty and a Notion link exists in the conversation, use the most recent one.
- If the target looks like a Notion URL (contains `notion.so` / `notion.site`) or a bare
  32-hex / dashed page ID → it is a **Notion source**.
- Otherwise → treat it as a **local markdown file path** and skip to Step 1.

For a **Notion source**, fetch it as markdown first:

```bash
notion-cli whoami
python3 "${CLAUDE_SKILL_DIR}/../_shared/notion/fetch_notion_markdown.py" "<notion-url-or-id>" \
  --output /tmp/create-prd-source.md --metadata /tmp/create-prd-source.json --check-auth
```

- If `whoami` or the fetch fails, tell the user authentication or page-share permission is
  required, include the failing command and a short stderr excerpt, and stop.
- Set the working source file to `/tmp/create-prd-source.md`.
- The fetch script lives in `skills/_shared/notion/` because `notion-do` uses the same one. If the
  path does not exist, the install is incomplete — tell the user to run `ai-skills update`.
- Derive `{name}` (used for the output directory in Step 2) from the Notion page **title**
  in `/tmp/create-prd-source.json` (fall back to the first H1 in the markdown), converted to
  an English kebab-case slug. Confirm the derived `{name}` with the user before writing files.

### Step 1: Read and Analyze Sections

1. Read the source markdown file (the local path, or `/tmp/create-prd-source.md` from Step 0).
2. Split by `## ` (H2 headings).
   - Content before the first H2 is the **overview** section.
   - Each H2 heading through the line before the next H2 is one section.
3. Identify each section's title and number.

### Step 2: Determine Output Directory

- The output directory is `{project-root}/docs/{name}/prd/`
  - `{project-root}` is the current working directory (project root).
  - `{name}` is the local source file's name without extension, or the slug derived from the
    Notion title in Step 0.
- Example: source file `~/Downloads/product-manage.md`, project root `/Users/me/my-app`
  → output directory: `/Users/me/my-app/docs/product-manage/prd/`

### Step 3: Create Per-Section Files

Save each section as its own file.

**Naming rules:**
- Overview: `0-overview.md`
- All others: `{number}-{english-slug}.md`
  - Example: `## 1. 분류` → `1-category.md`
  - Example: `## 3. 옵션설정` → `3-option-settings.md`
  - Convert Korean section titles to appropriate English slugs.

**Content cleanup rules (always apply):**

1. **Remove image links**
   - Delete all `![...](...)` image markdown.
   - Also remove blank lines that contained only an image.

2. **Handle Notion links**
   - Links pointing to a section within the same document → convert to a relative path of the split file
     - Example: `[1. 분류](https://www.notion.so/...)` → `[1. 분류](./1-category.md)`
   - Links pointing to an external Notion document → keep the link text, empty the URL
     - Example: `[외부 문서](https://www.notion.so/...)` → `[외부 문서]()`
   - **Decision rule**: if the link text contains a section title or number from the current document, treat as internal; otherwise external.

### Step 4: Create Overview File

`0-overview.md` must include the original overview content plus **a link list to every split file**.

**Format:**

```markdown
{original overview content (with image/Notion link cleanup applied)}

---

## Table of Contents

- [1. Category](./1-category.md)
- [2. Product](./2-product.md)
- [3. Option Settings](./3-option-settings.md)
- ...
```

### Step 5: Report Results

After splitting, show the user the generated file list as a tree. For a Notion source,
also state the resolved page title and the `{name}` slug used.

## Notes

- Do not modify or delete the original file.
- For a Notion source, the fetched `/tmp/create-prd-source.md` is a scratch copy — the split
  files under `docs/{name}/prd/` are the real output.
- If the output directory already exists, ask the user whether to overwrite.
- Keep HTML blocks such as `<aside>` in place within their section.
- Keep strikethrough (`~~`) content as-is.
