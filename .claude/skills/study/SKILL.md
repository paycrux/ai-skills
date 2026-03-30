---
name: study
description: Write a study report from the current conversation. Analyzes the problem, approaches tried, why they failed, and the final solution as a learning document.
argument-hint: [file-path] [requirements]
---

# /study - Conversation-based Study Report

Writes a study report from the current conversation. Think of this as a **research document** — the goal is to deeply understand the technology and problem, not just log what happened.

## Argument Parsing

- `/study` — Save report as a new markdown file in `<project-root>/.claude/study/`
- `/study <file-path>` — Append report to the specified file (preserve existing content)
- `/study <requirements>` — Adjust report scope/perspective based on requirements, save to `<project-root>/.claude/study/`

Parse `$ARGUMENTS` to distinguish the 3 cases:
- If it looks like a file path (starts with `/`, `./`, `../`, `~`, or `@`, or contains file extensions like `.md`, `.txt`) → treat as file path (remove leading `@` if present)
- Other text → treat as requirements
- Empty → save to `<project-root>/.claude/study/`

## Default Save Location

When no file path is specified (both empty args and requirements-only args), save the report as a new markdown file:
- Path: `<project-root>/.claude/study/{topic-slug}.md`
- File name: descriptive kebab-case slug derived from the topic (e.g., `react-native-animation-reanimated.md`, `zustand-state-management.md`)
- If the file already exists, append to it following the "When Appending to a File" rules below

## Context-Aware Writing

Before writing, **read the target file first** (if appending). Analyze what's already documented:

- If foundational concepts are already well-explained → **only add the new case study/analysis**
- If the topic is new or the file doesn't exist → **write both the technical foundation AND the case study**

### When adding to an existing document:

1. Read the file and understand its structure (numbered sections, heading style, depth level)
2. Continue the existing numbering and style
3. Add only what's new — don't repeat concepts already covered
4. Connect the new case to existing concepts where relevant (e.g., "이전 섹션 4의 reset 문제와 동일한 원인")

### When writing a new document:

Write two parts:

**Part 1: Technical Foundation**
- What is this technology/concept?
- Core APIs/methods with usage examples and visual diagrams (use ASCII art for stack/state diagrams)
- Common patterns and when to use each
- Summary table for quick reference

**Part 2: Case Study** (same structure as below)

## Case Study Structure

```markdown
## {Section Number}. {Topic} - {Date}

> Background: {What problem was being solved, 1-2 lines}

### Problem

{Specific symptoms with concrete flow diagrams}

### Approaches Tried

For each approach:

#### Approach N: {Method Name}

- **Code**: Key code snippet (concise)
- **Result**: What happened
- **Why it failed**: Root cause analysis (this is the key!)

### Final Solution

- **Method**: {The final chosen approach}
- **Code**: Key code
- **Why this works**: Explanation of the underlying mechanism

### Key Takeaways

- Principles learned from this experience (3-5)
- How to approach similar situations next time
```

## Writing Principles

1. **"Why it failed" is the most important part** — Not just listing, but root cause analysis of the underlying mechanism
2. **Minimal code** — Only the essential parts, not the full code
3. **Logical order, not chronological** — Group similar approaches together
4. **Reusable takeaways** — Universal principles, not project-specific ones
5. **Respect the user's actual results** — If the user said "performance was bad", record it as-is without speculation
6. **Use visual diagrams** — ASCII stack/state diagrams make navigation flows much clearer than text alone
7. **Connect to fundamentals** — Explain WHY something works at the framework level, not just that it works

## When Appending to a File

- Read existing file content first with Read tool
- Match the existing document's numbering, heading style, and depth
- Add new section after a `---` separator at the end
- Never modify existing content
