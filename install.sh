#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────
# ai-skills installer
# https://github.com/paycrux/ai-skills
# ─────────────────────────────────────────────

REPO_URL="https://github.com/paycrux/ai-skills.git"
MARKER_START="<!-- AI-SKILLS:START -->"
MARKER_END="<!-- AI-SKILLS:END -->"
VERSION="0.13.0"

# Permanent state directory (persists across installs so `ai-skills update` works)
AI_SKILLS_HOME="$HOME/.ai-skills"
AI_SKILLS_REPO="$AI_SKILLS_HOME/repo"
AI_SKILLS_BIN="$AI_SKILLS_HOME/bin"
INSTALLS_JSON="$AI_SKILLS_HOME/installs.json"

# Dedicated PATH markers for shell rc files (separate from the CLAUDE.md markers)
PATH_MARKER_START="# AI-SKILLS-PATH:START"
PATH_MARKER_END="# AI-SKILLS-PATH:END"

# Set by register_path when a shell rc is modified — drives the final reload notice
NEED_SHELL_RELOAD=""

# Lazily bind fd 3 to an interactive input source (stdin if it's a tty, else
# /dev/tty for the `curl | bash` case). Only called right before a prompt
# actually needs to read something — fully-flagged, non-interactive runs
# (CI, `--claude --global --update`, etc.) never touch this and never need
# a controlling terminal.
TTY_READY=false
ensure_tty() {
  $TTY_READY && return 0
  if [[ -t 0 ]]; then
    exec 3<&0
    TTY_READY=true
    return 0
  fi
  if { exec 3</dev/tty; } 2>/dev/null; then
    TTY_READY=true
    return 0
  fi
  return 1
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[info]${NC} $1"; }
ok()    { echo -e "${GREEN}[ok]${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# ─────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────
ONLY=""
UPDATE=false
MODE=""        # claude | cursor | codex
SCOPE=""       # global | project
LOCAL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --claude)
      MODE="claude"
      shift
      ;;
    --cursor)
      MODE="cursor"
      shift
      ;;
    --codex)
      MODE="codex"
      shift
      ;;
    --global)
      SCOPE="global"
      shift
      ;;
    --project)
      SCOPE="project"
      shift
      ;;
    --only)
      ONLY="$2"
      shift 2
      ;;
    --update)
      UPDATE=true
      shift
      ;;
    --local)
      LOCAL=true
      shift
      ;;
    --help|-h)
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Target (required):"
      echo "  --claude          Install for Claude Code"
      echo "  --cursor          Install for Cursor"
      echo "  --codex           Install for Codex"
      echo ""
      echo "Scope:"
      echo "  --global          Install to ~/.claude, ~/.cursor, or ~/.codex (all projects)"
      echo "  --project         Install to ./.claude, ./.cursor, or ./.codex (current project only)"
      echo ""
      echo "Options:"
      echo "  --only <type>     Install specific type only: skills, rules, docs"
      echo "  --update          Update existing installation (safe merge)"
      echo "  --local           Use local .claude/ as source (skip git clone)"
      echo "  -h, --help        Show this help"
      echo ""
      echo "Examples:"
      echo "  bash install.sh --claude --global            # Claude Code, all projects"
      echo "  bash install.sh --claude --project           # Claude Code, this project"
      echo "  bash install.sh --cursor --global            # Cursor, all projects"
      echo "  bash install.sh --cursor --project           # Cursor, this project"
      echo "  bash install.sh --codex --global             # Codex, all projects"
      echo "  bash install.sh --codex --project            # Codex, this project"
      echo "  bash install.sh --claude --global --update   # Update existing"
      echo "  bash install.sh --claude --global --only skills"
      echo "  bash install.sh --claude --global --local    # Use local source"
      exit 0
      ;;
    *)
      error "Unknown option: $1 (use --help)"
      ;;
  esac
done

# ─────────────────────────────────────────────
# Prerequisites: git (clone) and python3 >= 3.9 (installer merges, flow scripts)
# ─────────────────────────────────────────────
python_ok() { command -v python3 >/dev/null && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; }

missing_tools() {
  local m=()
  command -v git >/dev/null || m+=("git")
  python_ok || m+=("python3 (3.9+)")
  echo "${m[*]:-}"
}

install_prereqs() {
  local os; os="$(uname -s)"
  if [[ "$os" == "Darwin" ]]; then
    if command -v brew >/dev/null; then
      brew install git python
    else
      # Command Line Tools ship git and python3; the installer is a GUI dialog, so wait for it to finish.
      xcode-select --install 2>/dev/null || true
      info "Finish the Command Line Tools dialog that just opened — waiting (Ctrl+C to stop)..."
      until xcode-select -p >/dev/null 2>&1 && command -v git >/dev/null && python_ok; do sleep 5; done
    fi
  elif command -v apt-get >/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y git python3
  elif command -v dnf >/dev/null; then
    sudo dnf install -y git python3
  elif command -v yum >/dev/null; then
    sudo yum install -y git python3
  else
    return 1
  fi
}

MISSING="$(missing_tools)"
if [[ -n "$MISSING" ]]; then
  warn "Required tools are missing: ${MISSING}"
  if ensure_tty; then
    read -rp "Install them now? [Y/n] " answer <&3
    case "${answer:-Y}" in
      [Yy]*) install_prereqs || error "No supported package manager found — install ${MISSING} yourself, then re-run this installer." ;;
      *) error "Install ${MISSING}, then re-run this installer." ;;
    esac
    MISSING="$(missing_tools)"
    [[ -z "$MISSING" ]] || error "Still missing after install: ${MISSING} — open a new terminal and re-run this installer."
    ok "Prerequisites installed"
  else
    error "Install ${MISSING}, then re-run this installer (no interactive terminal to ask)."
  fi
fi

# ─────────────────────────────────────────────
# Interactive selection if not specified
# ─────────────────────────────────────────────
if [[ -z "$MODE" ]]; then
  ensure_tty || error "No interactive terminal available — run with explicit flags: bash install.sh --claude --global (see --help)"
  echo ""
  echo -e "${CYAN}Which editor?${NC}"
  echo "  1) Claude Code"
  echo "  2) Cursor"
  echo "  3) Codex"
  read -rp "> " choice <&3
  case $choice in
    1) MODE="claude" ;;
    2) MODE="cursor" ;;
    3) MODE="codex" ;;
    *) error "Invalid choice" ;;
  esac
fi

if [[ -z "$SCOPE" ]]; then
  ensure_tty || error "No interactive terminal available — run with explicit flags: bash install.sh --${MODE} --global (see --help)"
  echo ""
  echo -e "${CYAN}Install scope?${NC}"
  echo "  1) Global  (~/.${MODE}/) — all projects"
  echo "  2) Project (./.${MODE}/) — current project only"
  read -rp "> " choice <&3
  case $choice in
    1) SCOPE="global" ;;
    2) SCOPE="project" ;;
    *) error "Invalid choice" ;;
  esac
fi

# Validate --only value
if [[ -n "$ONLY" ]] && [[ "$ONLY" != "skills" && "$ONLY" != "rules" && "$ONLY" != "docs" ]]; then
  error "--only must be one of: skills, rules, docs"
fi

# ─────────────────────────────────────────────
# Determine target directory
# ─────────────────────────────────────────────
if [[ "$SCOPE" == "global" ]]; then
  TARGET_DIR="$HOME/.${MODE}"
else
  TARGET_DIR="$(pwd)/.${MODE}"
fi

# Auto-detect existing installation for interactive mode
if [[ -d "$TARGET_DIR/skills" || -d "$TARGET_DIR/rules" ]]; then
  if ! $UPDATE && ! ensure_tty; then
    warn "Existing installation detected at ${TARGET_DIR}/ — no interactive terminal available, defaulting to fresh install (skip existing files). Pass --update to overwrite changed files."
  elif ! $UPDATE; then
    echo ""
    warn "Existing installation detected at ${TARGET_DIR}/"
    echo -e "  ${CYAN}1)${NC} Update (overwrite changed files with confirmation)"
    echo -e "  ${CYAN}2)${NC} Fresh install (skip existing files)"
    read -rp "> " choice <&3
    case $choice in
      1) UPDATE=true ;;
      2) ;;
      *) error "Invalid choice" ;;
    esac
  fi
fi

# For Cursor project installs, AGENTS.md goes to project root
PROJECT_ROOT="$(pwd)"

# ─────────────────────────────────────────────
# Resolve source directory
# ─────────────────────────────────────────────
if $LOCAL; then
  # Use the repo root where install.sh lives
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SRC_DIR="$SCRIPT_DIR/.claude"
  if [[ ! -d "$SRC_DIR" ]]; then
    error ".claude directory not found next to install.sh"
  fi
  info "Using local source: $SRC_DIR"
else
  # Permanent clone at ~/.ai-skills/repo — kept across installs so `ai-skills update` can pull.
  mkdir -p "$AI_SKILLS_HOME"
  if [[ -d "$AI_SKILLS_REPO/.git" ]]; then
    info "Updating ai-skills repository ($AI_SKILLS_REPO)..."
    if ! git -C "$AI_SKILLS_REPO" pull --ff-only --quiet; then
      error "Failed to update $AI_SKILLS_REPO (git pull --ff-only failed).
  The permanent clone may be dirty, mid-rebase, or diverged from the remote.
  Fix: rm -rf $AI_SKILLS_REPO   then re-run this installer."
    fi
  else
    info "Cloning ai-skills repository to $AI_SKILLS_REPO..."
    git clone --quiet "$REPO_URL" "$AI_SKILLS_REPO" \
      || error "git clone failed — check your network or the repository URL ($REPO_URL)."
  fi
  SRC_DIR="$AI_SKILLS_REPO/.claude"

  if [[ ! -d "$SRC_DIR" ]]; then
    error ".claude directory not found in repository"
  fi
fi

# ─────────────────────────────────────────────
# Helper: copy files safely
# ─────────────────────────────────────────────
copy_dir() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ ! -d "$src" ]]; then
    warn "Source not found: $label — skipping"
    return
  fi

  mkdir -p "$dest"
  local count=0
  local skipped=0

  while IFS= read -r -d '' file; do
    local rel="${file#$src/}"
    local dest_file="$dest/$rel"

    mkdir -p "$(dirname "$dest_file")"

    if [[ -f "$dest_file" ]]; then
      if $UPDATE; then
        if diff -q "$file" "$dest_file" > /dev/null 2>&1; then
          skipped=$((skipped + 1))
        else
          info "Updated: $label/$rel"
          cp "$file" "$dest_file"
          count=$((count + 1))
        fi
      else
        warn "Skipped (already exists): $label/$rel"
        skipped=$((skipped + 1))
      fi
    else
      cp "$file" "$dest_file"
      count=$((count + 1))
    fi
  done < <(find "$src" -type f -print0)

  ok "$label: ${count} files installed"
  if [[ $skipped -gt 0 ]]; then
    if $UPDATE; then
      info "$label: ${skipped} files unchanged or skipped"
    else
      warn "$label: ${skipped} files skipped (already exist, use --update to overwrite)"
    fi
  fi
}

# ─────────────────────────────────────────────
# Helper: clean up removed skills from previous versions
# ─────────────────────────────────────────────
cleanup_legacy_skills() {
  local skills_dir="$1/skills"
  if [[ ! -d "$skills_dir" ]]; then
    return
  fi

  local removed_skills=(
    "git-branch"
    "pr"
    "test-case"
    "evaluate"
    "finalize"
    "investigate"
    "caveman"
    "qa-guide"
    "task-plan"
    "implement"
    "qa"
    "tracker"
  )

  local cleaned=0
  for skill in "${removed_skills[@]}"; do
    if [[ -d "$skills_dir/$skill" ]]; then
      rm -rf "$skills_dir/$skill"
      cleaned=$((cleaned + 1))
    fi
  done

  if [[ $cleaned -gt 0 ]]; then
    ok "Cleaned up ${cleaned} legacy skill directories (git-branch/pr consolidated into git-pr in v0.4.3; test-case merged into qa-guide in v0.4.6; evaluate/finalize removed in v0.4.7; investigate merged into task-plan; caveman removed in v0.10.0; qa-guide removed; task-plan/implement/qa merged into flow; tracker replaced by flow feature documents)"
  fi
}

# ─────────────────────────────────────────────
# Helper: clean up removed agents from previous versions
# ─────────────────────────────────────────────
cleanup_legacy_agents() {
  local agents_dir="$1/agents"
  if [[ ! -d "$agents_dir" ]]; then
    return
  fi

  local removed_agents=(
    "evaluate-a11y.md"
    "evaluate-docs.md"
    "evaluate-engineering.md"
    "evaluate-performance.md"
    "evaluate-react.md"
    "evaluate-security.md"
    "implement-engineering.md"
    "implement-react.md"
  )

  local cleaned=0
  for agent in "${removed_agents[@]}"; do
    if [[ -f "$agents_dir/$agent" ]]; then
      rm "$agents_dir/$agent"
      cleaned=$((cleaned + 1))
    fi
  done

  if [[ $cleaned -gt 0 ]]; then
    ok "Cleaned up ${cleaned} legacy agent files (sub-agents removed in v0.4.0)"
  fi

  # Remove agents directory if empty
  if [[ -d "$agents_dir" ]] && [[ -z "$(ls -A "$agents_dir" 2>/dev/null)" ]]; then
    rmdir "$agents_dir"
    info "Removed empty agents/ directory"
  fi
}

# ─────────────────────────────────────────────
# Helper: clean up scripts that moved into skills/_shared/
# (fetch_notion_markdown.py was duplicated in create-prd and notion-do)
# ─────────────────────────────────────────────
cleanup_moved_scripts() {
  local skills_dir="$1/skills"
  if [[ ! -d "$skills_dir" ]]; then
    return
  fi

  local moved_paths=(
    "create-prd/scripts/fetch_notion_markdown.py"
    "notion-do/scripts/fetch_notion_markdown.py"
  )

  local cleaned=0
  for path in "${moved_paths[@]}"; do
    local full="$skills_dir/$path"
    if [[ -f "$full" ]]; then
      rm -f "$full"
      cleaned=$((cleaned + 1))
      # drop the scripts/ directory too, if nothing else is in it
      local parent
      parent="$(dirname "$full")"
      if [[ -d "$parent" ]] && [[ -z "$(ls -A "$parent" 2>/dev/null)" ]]; then
        rmdir "$parent"
      fi
    fi
  done

  if [[ $cleaned -gt 0 ]]; then
    ok "Cleaned up ${cleaned} duplicated scripts (fetch_notion_markdown.py moved to skills/_shared/notion/ in v0.10.0)"
  fi
}

# ─────────────────────────────────────────────
# Helper: merge CLAUDE.md with markers
# ─────────────────────────────────────────────
merge_claude_md() {
  local src_content
  src_content=$(cat "$SRC_DIR/CLAUDE.md")
  local dest_file="$TARGET_DIR/CLAUDE.md"
  local marked_content="${MARKER_START}
${src_content}
${MARKER_END}"

  if [[ ! -f "$dest_file" ]]; then
    echo "$marked_content" > "$dest_file"
    ok "CLAUDE.md created"
    return
  fi

  if grep -qF "$MARKER_START" "$dest_file"; then
    local tmp first_start last_end
    tmp=$(mktemp)
    first_start=$(grep -nF "$MARKER_START" "$dest_file" | head -1 | cut -d: -f1)
    last_end=$(grep -nF "$MARKER_END" "$dest_file" | tail -1 | cut -d: -f1)
    {
      [[ "$first_start" -gt 1 ]] && head -n "$((first_start - 1))" "$dest_file"
      echo "$marked_content"
      tail -n +"$((last_end + 1))" "$dest_file" 2>/dev/null || true
    } > "$tmp"
    mv "$tmp" "$dest_file"
    ok "CLAUDE.md updated (ai-skills section replaced)"
  else
    # Remove any existing (unmarked) copy of src_content before prepending
    local tmp_py tmp_stripped stripped
    tmp_py=$(mktemp)
    tmp_stripped=$(mktemp)
    cat > "$tmp_py" <<'PYEOF'
import sys
dest_path, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(dest_path) as f:
    existing = f.read()
with open(src_path) as f:
    src = f.read().rstrip()
stripped = existing.replace(src, '').strip()
with open(out_path, 'w') as f:
    f.write(stripped)
PYEOF
    python3 "$tmp_py" "$dest_file" "$SRC_DIR/CLAUDE.md" "$tmp_stripped"
    stripped=$(cat "$tmp_stripped")
    rm -f "$tmp_py" "$tmp_stripped"
    {
      echo "$marked_content"
      if [[ -n "$stripped" ]]; then
        echo ""
        echo "$stripped"
      fi
    } > "$dest_file"
    ok "CLAUDE.md merged (ai-skills section prepended)"
  fi
}

# ─────────────────────────────────────────────
# Helper: per-rule Cursor metadata (description|globs)
# Any rules/*.md without an entry still ships, with a generic description.
# ─────────────────────────────────────────────
rule_mdc_meta() {
  case "$1" in
    react-typescript)
      echo 'React + TypeScript 프론트엔드 구현 시 적용|["*.tsx", "*.ts"]' ;;
    frontend-design)
      echo '디자인 레퍼런스 없이 UI를 직접 만들 때 적용|["*.tsx", "*.css", "*.scss"]' ;;
    writing)
      echo '사람이 읽는 산문(계획 문서, 진행 기록, PR 본문, QA 가이드)을 쓸 때 적용|["*.md"]' ;;
    *)
      echo "ai-skills rule: $1|[]" ;;
  esac
}

# ─────────────────────────────────────────────
# Helper: create Cursor .mdc rule file
# ─────────────────────────────────────────────
create_mdc_rule() {
  local src_file="$1"
  local dest_file="$2"
  local description="$3"
  local globs="$4"

  if [[ -f "$dest_file" ]] && ! $UPDATE; then
    warn "Skipped (already exists): $(basename "$dest_file")"
    return 1
  fi

  local content
  content=$(cat "$src_file")

  cat > "$dest_file" <<MDCEOF
---
description: ${description}
globs: ${globs}
alwaysApply: false
---

${content}
MDCEOF
  return 0
}

# ─────────────────────────────────────────────
# Helper: merge AGENTS.md with markers
# ─────────────────────────────────────────────
merge_agents_md() {
  local dest_file="$1/AGENTS.md"
  local marked_content
  marked_content="${MARKER_START}
# AGENTS.md

## Task Planning

사용자가 새로운 기능 개발, 버그 수정 등 작업을 요청하면 계획 여부를 묻지 않고 요청에서 경로를 고른다:
- 기획서(PRD)나 Figma 링크가 있거나 여러 화면·파일에 걸치면 → .cursor/skills/flow/SKILL.md 를 읽고 그대로 따른다
- 여러 Jira 스토리에 걸치면 → .cursor/skills/flow/references/feature.md 를 읽고 flow 기능 문서 초안부터 쓴다
- 그 외 → 바로 진행하고, 바꾼 내용을 한 줄로 보고한다

## Implementation Rules

All code changes are executed directly — no sub-agents.

- Follow \`.cursor/rules/react-typescript.mdc\` for frontend code
- Follow existing patterns discovered in codebase exploration
- When using the flow skill, the workflow orchestrates phases — but code is written directly

### Exceptions (direct edit without workflow)
- Config file changes (package.json, tsconfig.json, .env, etc.)
- Documentation file changes (*.md)
- Simple typo/naming fixes (1-2 line changes)
- Import path corrections
- Lint/format fixes

## Available Workflows

| Workflow | File | Purpose |
|----------|------|---------|
| flow | @.cursor/skills/flow/SKILL.md | PRD → Figma SOT map → questions → plan → build → verify, as JSON docs per domain rendered to linked static HTML pages |
| study | @.cursor/skills/study/SKILL.md | Study report writing |

## Plan Storage Path

flow documents are stored in \`docs/<domain>/\` (task JSON under \`docs/<domain>/tasks/\`). Plans under \`docs/*/plans/\` predate flow and are read only.

## Session Handoff

If there's work in progress:
1. Find the flow task whose stage is \`now\` or \`ask\` and read it with \`flow.py brief <task.json>\`
2. Report current status and continue after user approval
${MARKER_END}"

  if [[ ! -f "$dest_file" ]]; then
    echo "$marked_content" > "$dest_file"
    ok "AGENTS.md created"
    return
  fi

  if grep -qF "$MARKER_START" "$dest_file"; then
    local tmp first_start last_end
    tmp=$(mktemp)
    first_start=$(grep -nF "$MARKER_START" "$dest_file" | head -1 | cut -d: -f1)
    last_end=$(grep -nF "$MARKER_END" "$dest_file" | tail -1 | cut -d: -f1)
    {
      [[ "$first_start" -gt 1 ]] && head -n "$((first_start - 1))" "$dest_file"
      echo "$marked_content"
      tail -n +"$((last_end + 1))" "$dest_file" 2>/dev/null || true
    } > "$tmp"
    mv "$tmp" "$dest_file"
    ok "AGENTS.md updated (ai-skills section replaced)"
  else
    local existing
    existing=$(cat "$dest_file")
    {
      echo "$marked_content"
      echo ""
      echo "$existing"
    } > "$dest_file"
    ok "AGENTS.md merged (ai-skills section prepended)"
  fi
}

# ─────────────────────────────────────────────
# Helper: upsert a marker-wrapped block into a file
# (create → replace existing marked block → prepend if unmarked)
# ─────────────────────────────────────────────
upsert_marked_file() {
  local dest_file="$1"
  local marked_content="$2"
  local label="$3"

  if [[ ! -f "$dest_file" ]]; then
    echo "$marked_content" > "$dest_file"
    ok "$label created"
    return
  fi

  if grep -qF "$MARKER_START" "$dest_file"; then
    local tmp first_start last_end
    tmp=$(mktemp)
    first_start=$(grep -nF "$MARKER_START" "$dest_file" | head -1 | cut -d: -f1)
    last_end=$(grep -nF "$MARKER_END" "$dest_file" | tail -1 | cut -d: -f1)
    {
      [[ "$first_start" -gt 1 ]] && head -n "$((first_start - 1))" "$dest_file"
      echo "$marked_content"
      tail -n +"$((last_end + 1))" "$dest_file" 2>/dev/null || true
    } > "$tmp"
    mv "$tmp" "$dest_file"
    ok "$label updated (ai-skills section replaced)"
  else
    local existing
    existing=$(cat "$dest_file")
    {
      echo "$marked_content"
      echo ""
      echo "$existing"
    } > "$dest_file"
    ok "$label merged (ai-skills section prepended)"
  fi
}

# ─────────────────────────────────────────────
# Helper: merge AGENTS.md for Codex (plain-md rule refs, ${ref}-relative paths)
# $1 = directory the AGENTS.md lives in
# $2 = path prefix used to reference skills/rules (".codex" for project,
#      "$HOME/.codex" for global)
# ─────────────────────────────────────────────
merge_agents_md_codex() {
  local dest_dir="$1"
  local ref="$2"
  local dest_file="$dest_dir/AGENTS.md"
  local marked_content
  marked_content="${MARKER_START}
# AGENTS.md

## Task Planning

사용자가 새로운 기능 개발, 버그 수정 등 작업을 요청하면 계획 여부를 묻지 않고 요청에서 경로를 고른다:
- 기획서(PRD)나 Figma 링크가 있거나 여러 화면·파일에 걸치면 → ${ref}/skills/flow/SKILL.md 를 읽고 그대로 따른다
- 여러 Jira 스토리에 걸치면 → ${ref}/skills/flow/references/feature.md 를 읽고 flow 기능 문서 초안부터 쓴다
- 그 외 → 바로 진행하고, 바꾼 내용을 한 줄로 보고한다

## Implementation Rules

All code changes are executed directly — no sub-agents.

- Follow ${ref}/rules/react-typescript.md for frontend code
- Follow existing patterns discovered in codebase exploration
- When using the flow skill, the workflow orchestrates phases — but code is written directly

### Exceptions (direct edit without workflow)
- Config file changes (package.json, tsconfig.json, .env, etc.)
- Documentation file changes (*.md)
- Simple typo/naming fixes (1-2 line changes)
- Import path corrections
- Lint/format fixes

## Available Workflows

| Workflow | File | Purpose |
|----------|------|---------|
| flow | ${ref}/skills/flow/SKILL.md | PRD → Figma SOT map → questions → plan → build → verify, as JSON docs per domain rendered to linked static HTML pages |
| study | ${ref}/skills/study/SKILL.md | Study report writing |

## Plan Storage Path

flow documents are stored in \`docs/<domain>/\` (task JSON under \`docs/<domain>/tasks/\`). Plans under \`docs/*/plans/\` predate flow and are read only.

## Session Handoff

If there's work in progress:
1. Find the flow task whose stage is \`now\` or \`ask\` and read it with \`flow.py brief <task.json>\`
2. Report current status and continue after user approval
${MARKER_END}"

  upsert_marked_file "$dest_file" "$marked_content" "AGENTS.md"
}

# ─────────────────────────────────────────────
# Helper: record this install so `ai-skills update` can replay it
# ─────────────────────────────────────────────
record_install() {
  # --local installs are dev/test only — never tracked as update targets
  $LOCAL && return

  mkdir -p "$AI_SKILLS_HOME"
  python3 - "$INSTALLS_JSON" "$MODE" "$SCOPE" "$TARGET_DIR" <<'PYEOF'
import json, sys, os

path, mode, scope, target = sys.argv[1:5]

data = []
if os.path.exists(path):
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
    except (ValueError, OSError):
        data = []

# dedupe by target_dir — a re-install of the same target updates the record in place
data = [e for e in data if isinstance(e, dict) and e.get("target_dir") != target]
data.append({"mode": mode, "scope": scope, "target_dir": target})

with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
  ok "Install recorded (${MODE}/${SCOPE} → ${TARGET_DIR})"
}

# ─────────────────────────────────────────────
# Helper: install the `ai-skills` CLI into ~/.ai-skills/bin
# ─────────────────────────────────────────────
install_cli() {
  # --local installs never register the global CLI (dev/test path)
  $LOCAL && return

  # SRC_DIR is "<repo>/.claude"; bin/ai-skills lives at the repo root
  local bin_src
  bin_src="$(dirname "$SRC_DIR")/bin/ai-skills"
  if [[ ! -f "$bin_src" ]]; then
    warn "bin/ai-skills not found in repository — skipping CLI install"
    return
  fi

  mkdir -p "$AI_SKILLS_BIN"
  cp "$bin_src" "$AI_SKILLS_BIN/ai-skills"
  chmod +x "$AI_SKILLS_BIN/ai-skills"
  ok "CLI installed → $AI_SKILLS_BIN/ai-skills"
}

# ─────────────────────────────────────────────
# Helper: register ~/.ai-skills/bin on PATH via the shell rc file
# ─────────────────────────────────────────────
register_path() {
  $LOCAL && return

  local shell_name rc
  shell_name="$(basename "${SHELL:-}")"
  case "$shell_name" in
    zsh)  rc="$HOME/.zshrc" ;;
    bash) rc="$HOME/.bashrc" ;;
    *)
      warn "Unsupported shell (${shell_name:-unknown}) — add this to your shell rc manually:"
      echo '  export PATH="$HOME/.ai-skills/bin:$PATH"'
      return
      ;;
  esac

  # Idempotent — skip if our marker block is already present
  if [[ -f "$rc" ]] && grep -qF "$PATH_MARKER_START" "$rc"; then
    info "PATH already registered in $rc"
    return
  fi

  {
    echo ""
    echo "$PATH_MARKER_START"
    echo 'export PATH="$HOME/.ai-skills/bin:$PATH"'
    echo "$PATH_MARKER_END"
  } >> "$rc"
  ok "PATH registered in $rc"
  NEED_SHELL_RELOAD="$rc"
}

# ─────────────────────────────────────────────
# Install
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ ai-skills installer v${VERSION} ━━━${NC}"
echo -e "${CYAN}    Mode: ${MODE} | Scope: ${SCOPE} | Target: ${TARGET_DIR}${NC}"
echo ""

mkdir -p "$TARGET_DIR"

# Clean up legacy agents and skills from previous versions
cleanup_legacy_skills "$TARGET_DIR"
cleanup_legacy_agents "$TARGET_DIR"
cleanup_moved_scripts "$TARGET_DIR"

if [[ "$MODE" == "claude" ]]; then
  # ── Claude Code install ──
  if [[ -z "$ONLY" ]]; then
    copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
    copy_dir "$SRC_DIR/rules"  "$TARGET_DIR/rules"  "rules"
    copy_dir "$SRC_DIR/docs"   "$TARGET_DIR/docs"   "docs"
    merge_claude_md
  else
    copy_dir "$SRC_DIR/$ONLY" "$TARGET_DIR/$ONLY" "$ONLY"
  fi

elif [[ "$MODE" == "cursor" ]]; then
  # ── Cursor install ──
  if [[ -z "$ONLY" || "$ONLY" == "skills" ]]; then
    copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
  fi

  if [[ -z "$ONLY" || "$ONLY" == "rules" ]]; then
    mkdir -p "$TARGET_DIR/rules"
    local_count=0

    # Every rules/*.md becomes an .mdc — adding a rule file needs no change here.
    for rule_file in "$SRC_DIR"/rules/*.md; do
      [[ -f "$rule_file" ]] || continue
      rule_name="$(basename "$rule_file" .md)"
      rule_meta="$(rule_mdc_meta "$rule_name")"
      if create_mdc_rule \
        "$rule_file" \
        "$TARGET_DIR/rules/${rule_name}.mdc" \
        "${rule_meta%%|*}" \
        "${rule_meta#*|}"; then
        local_count=$((local_count + 1))
      fi
    done

    ok "rules: ${local_count} .mdc files created"
  fi

  # AGENTS.md — project scope only (global scope doesn't have a project root)
  if [[ -z "$ONLY" ]]; then
    if [[ "$SCOPE" == "project" ]]; then
      merge_agents_md "$PROJECT_ROOT"
    else
      info "AGENTS.md is project-specific. To add it, run with --project in your project directory."
    fi
  fi

elif [[ "$MODE" == "codex" ]]; then
  # ── Codex install (Cursor-style wiring; plain-md rules, AGENTS.md) ──
  if [[ -z "$ONLY" ]]; then
    copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
    copy_dir "$SRC_DIR/rules"  "$TARGET_DIR/rules"  "rules"

    # AGENTS.md — Codex reads it globally (~/.codex/AGENTS.md) and per project (root)
    if [[ "$SCOPE" == "global" ]]; then
      merge_agents_md_codex "$TARGET_DIR" "$TARGET_DIR"
    else
      merge_agents_md_codex "$PROJECT_ROOT" ".codex"
    fi
  else
    copy_dir "$SRC_DIR/$ONLY" "$TARGET_DIR/$ONLY" "$ONLY"
  fi
fi

# ─────────────────────────────────────────────
# Record install + set up the `ai-skills` CLI
# ─────────────────────────────────────────────
record_install
install_cli
register_path

# Note: browse (headless browser) is intentionally NOT built here.
# /browse detects a missing binary on first use and builds it then —
# see the "Setup" step in its SKILL.md.

echo ""
ok "Done! ai-skills installed to ${TARGET_DIR}/"
echo ""

if ! $LOCAL; then
  echo -e "  ${CYAN}Update:${NC}  ai-skills update"
  echo -e "          (또는 CLI 미등록 환경: curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --${MODE} --${SCOPE} --update)"
  echo ""
  if [[ -n "$NEED_SHELL_RELOAD" ]]; then
    warn "'ai-skills' 커맨드를 쓰려면 새 터미널을 열거나 다음을 실행하세요:"
    echo -e "    source $NEED_SHELL_RELOAD"
    echo ""
  fi
  info "PATH 우선순위 확인: which ai-skills  (다른 동명 실행 파일이 앞설 수 있음)"
  echo ""
else
  echo -e "  ${CYAN}Update:${NC}  curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --${MODE} --${SCOPE} --update"
  echo ""
fi
