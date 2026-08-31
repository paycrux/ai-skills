# SKILL.md Frontmatter Specification

## All Available Fields

```yaml
---
name: my-skill                      # Lowercase, hyphens, max 64 chars. Uses dir name if omitted.
description: "What + When"          # Max 1024 chars. Effective 250 chars in listing. REQUIRED.
argument-hint: "[issue-number]"     # Shown during autocomplete. Optional.
disable-model-invocation: true      # Prevents Claude from auto-triggering. For side-effectful skills.
user-invocable: false               # Hides from / menu. For passive knowledge skills.
allowed-tools: Read, Grep, Glob     # Tools usable without per-use approval. Optional.
model: claude-opus-5                # Override model. Optional.
effort: high                        # low | medium | high | max. Only on models that support effort control. Optional.
context: fork                       # Runs in isolated subagent context. Optional.
agent: Explore                      # Built-in or custom agent. Requires context: fork. Optional.
paths: "src/**/*.ts,*.go"           # Auto-activates only for matching file patterns. Optional.
shell: bash                         # bash (default) or powershell. Optional.
---
```

## Field Guidelines

### name
- Gerund form preferred: `processing-pdfs`, `managing-databases`
- Lowercase + hyphens only, max 64 chars
- If omitted, directory name is used

### description
- **Most important field** — determines when Claude triggers the skill
- Front-load the key use case (first 250 chars shown in listing)
- Include both **what it does** AND **trigger conditions**
- Write in third person

Good:
```
"Scaffold and author Claude Code skills with proper structure and best practices. Use when creating, refactoring, or reviewing skills."
```

Bad:
```
"A tool for making skills" # Too vague, no triggers
```

### disable-model-invocation
Set `true` for skills with side effects:
- Deploy, push, publish
- Send messages (Slack, email, GitHub)
- Commit, merge, delete
- Any action visible to others

### user-invocable
Set `false` for passive knowledge skills:
- Style guides, coding conventions
- Domain context (legacy system docs)
- Skills that Claude should apply automatically, not on command

### context: fork
- Runs skill in isolated subagent (separate context window)
- Only useful for skills with explicit task instructions
- Not useful for passive knowledge/guideline skills
- Combine with `agent:` to specify which agent type

### allowed-tools
- Comma-separated list of tools the skill can use without user approval
- Reduces permission prompts for trusted operations
- Example: `Read, Grep, Glob, Agent, Bash`

## String Substitutions

Available inside SKILL.md body:

| Variable | Description |
|---|---|
| `$ARGUMENTS` | All arguments passed at invocation |
| `$ARGUMENTS[N]` or `$N` | Nth positional argument (0-based) |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Absolute path to the skill's directory |
| `` !`command` `` | Shell command output injected before Claude sees the prompt |
