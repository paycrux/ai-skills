---
name: investigate
description: "Lightweight debugging workflow for systematic root cause analysis. Collects symptoms, generates hypotheses, runs verification loops, and records findings. Use instead of /task-plan when quick debugging is needed without full planning overhead."
argument-hint: "[symptom description or error message]"
allowed-tools: ["Agent", "Read", "Glob", "Grep", "Bash", "Write", "Edit"]
effort: "high"
---

# /investigate — Systematic Debugging Workflow

Lightweight root cause analysis for bugs and unexpected behavior. Faster than `/task-plan` — no 5-file document set, just focused investigation with structured output.

## When to Use

| Situation | Use |
|---|---|
| Known bug, need root cause | `/investigate` |
| New feature or large change | `/task-plan` |
| Quick fix, cause already known | Direct fix |
| Production incident, need fast analysis | `/investigate` |

## Argument Parsing

- `/investigate <symptom>` — start investigation from described symptom
- `/investigate <error message>` — start from error trace
- `/investigate <file-path>` — investigate suspicious behavior in specific file
- `/investigate` — ask user to describe the problem

## Execution

### Step 1: Symptom Collection

Gather all available evidence before forming any hypothesis.

**From user input:**
- Error message / stack trace
- Steps to reproduce
- Expected vs actual behavior
- When it started (recent change?)

**From codebase (collect silently):**
- `git log --oneline -10` — recent changes
- `git diff HEAD~3 --name-only` — recently modified files
- Relevant error logs or test output if available

Organize into the symptom block format defined in `${CLAUDE_SKILL_DIR}/templates/symptom-block.md`.

### Step 2: Hypothesis Generation

Generate 2-4 hypotheses ranked by probability. Use the template at `${CLAUDE_SKILL_DIR}/templates/hypothesis.md`.

For each hypothesis:
1. **What**: one-line description of the suspected cause
2. **Why likely**: evidence supporting this hypothesis
3. **How to verify**: specific code location or test to confirm/reject
4. **Probability**: High / Medium / Low

Present hypotheses to user and ask:
> "다음 가설 중 어떤 것부터 검증할까요? 또는 다른 가설이 있으면 알려주세요."

### Step 3: Verification Loop

For the selected hypothesis, run the verify-reject cycle:

```
┌─ Verify hypothesis
│   ├─ Read suspected code
│   ├─ Trace data flow
│   ├─ Check edge cases
│   └─ Run related test if exists
│
├─ Confirmed? → Step 4 (Root Cause)
├─ Rejected? → Log why, move to next hypothesis
└─ Partially? → Refine hypothesis, re-verify
```

**Rules for verification:**
- Read actual code — don't guess based on file names
- Trace the full execution path, not just the suspected line
- Check git blame for recent changes to suspected area
- If all hypotheses rejected → generate new ones from what was learned

**Max 3 loops** — if root cause not found after 3 hypothesis cycles, escalate:
> "3회 검증 후에도 원인을 특정하지 못했습니다. 지금까지 확인한 내용을 정리해드릴까요, 아니면 다른 접근이 필요할까요?"

### Step 4: Root Cause Documentation

When root cause is confirmed, document it using the template at `${CLAUDE_SKILL_DIR}/templates/findings.md`.

Present to user:
> "원인을 찾았습니다. 수정을 진행할까요?"

### Step 5: Fix (Optional)

If user approves:
1. Propose the minimal fix
2. Execute via appropriate agent (implement-engineering or implement-react per CLAUDE.md rules)
3. Verify fix resolves the symptom

If user declines or wants to fix themselves:
- Save the findings document and end

### Step 6: Save Investigation

Follow the save policy at `${CLAUDE_SKILL_DIR}/templates/save-policy.md`.

## Rules

- **Hypotheses first, code reading second** — don't scatter-read the whole codebase
- **Verify one hypothesis at a time** — don't mix verification of multiple causes
- **Log rejected hypotheses** — they're valuable for future debugging
- **Ask user before fixing** — investigation ≠ automatic fix
- **Max 3 verification loops** — escalate if stuck
- **Write output in Korean**
