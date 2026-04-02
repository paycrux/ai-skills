#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────
# ai-skills installer
# https://github.com/paycrux/ai-skills
# ─────────────────────────────────────────────

REPO_URL="https://github.com/paycrux/ai-skills.git"
MARKER_START="<!-- AI-SKILLS:START -->"
MARKER_END="<!-- AI-SKILLS:END -->"
VERSION="0.3.0"

# Ensure interactive input works even when piped (curl | bash)
if [[ ! -t 0 ]]; then
  exec 3</dev/tty || error "Cannot open /dev/tty — run with explicit flags: bash install.sh --claude --global"
else
  exec 3<&0
fi

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
MODE=""        # claude | cursor
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
      echo ""
      echo "Scope:"
      echo "  --global          Install to ~/.claude or ~/.cursor (all projects)"
      echo "  --project         Install to ./.claude or ./.cursor (current project only)"
      echo ""
      echo "Options:"
      echo "  --only <type>     Install specific type only: skills, agents, rules"
      echo "  --update          Update existing installation (safe merge)"
      echo "  --local           Use local .claude/ as source (skip git clone)"
      echo "  -h, --help        Show this help"
      echo ""
      echo "Examples:"
      echo "  bash install.sh --claude --global            # Claude Code, all projects"
      echo "  bash install.sh --claude --project           # Claude Code, this project"
      echo "  bash install.sh --cursor --global            # Cursor, all projects"
      echo "  bash install.sh --cursor --project           # Cursor, this project"
      echo "  bash install.sh --claude --global --update   # Update existing"
      echo "  bash install.sh --claude --global --only skills"
      echo "  bash install.sh --claude --global --local      # Use local source"
      exit 0
      ;;
    *)
      error "Unknown option: $1 (use --help)"
      ;;
  esac
done

# ─────────────────────────────────────────────
# Interactive selection if not specified
# ─────────────────────────────────────────────
if [[ -z "$MODE" ]]; then
  echo ""
  echo -e "${CYAN}Which editor?${NC}"
  echo "  1) Claude Code"
  echo "  2) Cursor"
  read -rp "> " choice <&3
  case $choice in
    1) MODE="claude" ;;
    2) MODE="cursor" ;;
    *) error "Invalid choice" ;;
  esac
fi

if [[ -z "$SCOPE" ]]; then
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
if [[ -n "$ONLY" ]] && [[ "$ONLY" != "skills" && "$ONLY" != "agents" && "$ONLY" != "rules" ]]; then
  error "--only must be one of: skills, agents, rules"
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
if [[ -d "$TARGET_DIR/skills" || -d "$TARGET_DIR/agents" || -d "$TARGET_DIR/rules" ]]; then
  if ! $UPDATE; then
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
  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT

  info "Cloning ai-skills repository..."
  git clone --depth 1 --quiet "$REPO_URL" "$TMP_DIR"
  SRC_DIR="$TMP_DIR/.claude"

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
          ((skipped++))
        else
          warn "Changed: $label/$rel"
          echo ""
          diff --color=auto -u "$dest_file" "$file" | head -30 || true
          echo ""
          echo -e "  ${CYAN}o)${NC} Overwrite  ${CYAN}s)${NC} Skip  ${CYAN}d)${NC} Show full diff"
          local answer=""
          while [[ "$answer" != "o" && "$answer" != "s" ]]; do
            read -rp "  > " answer <&3
            if [[ "$answer" == "d" ]]; then
              diff --color=auto -u "$dest_file" "$file" || true
              echo ""
              echo -e "  ${CYAN}o)${NC} Overwrite  ${CYAN}s)${NC} Skip"
            fi
          done
          if [[ "$answer" == "o" ]]; then
            cp "$file" "$dest_file"
            ((count++))
          else
            ((skipped++))
          fi
        fi
      else
        warn "Skipped (already exists): $label/$rel"
        ((skipped++))
      fi
    else
      cp "$file" "$dest_file"
      ((count++))
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

사용자가 새로운 기능 개발, 버그 수정 등 작업을 요청하면:
- \"task-plan 스킬을 사용해서 작업 계획을 먼저 세울까요, 아니면 바로 진행할까요?\" 를 먼저 물어본다
- 계획이 필요없다고 하면 → 바로 진행
- 계획 작성을 원하면 → .cursor/skills/task-plan/SKILL.md 를 읽고 그대로 따른다
- 사용자가 디자인 문서나 요구사항을 첨부하면 → 분석 후 스킬 플로우에 반영

## 구현 규칙

코드 변경 작업(구현, 수정, 버그 수정, 리팩토링 등)을 수행할 때 **반드시 전문 에이전트를 사용한다.**

### 에이전트 선택 기준

| 작업 유형 | 에이전트 파일 |
|-----------|--------------|
| 타입/인터페이스, API 클라이언트, 유틸, 서비스, 상태관리 셋업, 데이터 변환 | @.cursor/agents/implement-engineering.md |
| 컴포넌트, 훅, 스타일링, 화면, 네비게이션, UI 상태 | @.cursor/agents/implement-react.md |
| 혼합 (데이터 레이어 + UI) | implement-engineering 먼저 → implement-react 순차 실행 |

### 에이전트 없이 직접 수정하는 경우 (예외)
- 설정 파일 변경 (package.json, tsconfig.json, .env 등)
- 문서 파일 변경 (*.md)
- 단순 오타/네이밍 수정 (1-2줄)
- import 경로 수정
- lint/format 수정

## 사용 가능한 워크플로우

| 워크플로우 | 파일 | 용도 |
|-----------|------|------|
| task-plan | @.cursor/skills/task-plan/SKILL.md | 작업 계획 수립 + 문서 생성 |
| implement | @.cursor/skills/implement/SKILL.md | 문서 기반 단계별 구현 |
| evaluate | @.cursor/skills/evaluate/SKILL.md | 코드 품질 종합 평가 (5개 에이전트 병렬) |
| qa-guide | @.cursor/skills/qa-guide/SKILL.md | QA 테스트 가이드 생성 |
| test-case | @.cursor/skills/test-case/SKILL.md | 테스트 케이스 생성 |
| study | @.cursor/skills/study/SKILL.md | 학습 보고서 작성 |

## 평가 에이전트

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| evaluate-docs | @.cursor/agents/evaluate-docs.md | task-plan 문서 품질 평가 |
| evaluate-react | @.cursor/agents/evaluate-react.md | React/RN 코드 품질 평가 |
| evaluate-engineering | @.cursor/agents/evaluate-engineering.md | TS/JS 엔지니어링 품질 평가 |
| evaluate-a11y | @.cursor/agents/evaluate-a11y.md | 접근성 (WCAG 2.1 AA) 평가 |
| evaluate-security | @.cursor/agents/evaluate-security.md | 프론트엔드 보안 평가 |
| evaluate-performance | @.cursor/agents/evaluate-performance.md | 프론트엔드 성능 평가 |

## Plan 저장 경로

모든 plan 문서는 \`docs/{task-name}/\` 에 저장한다.

## Task-plan 문서 최신화

구현 중 task-plan의 원인 분석이나 접근 방식이 실제와 다르다고 판단되면:

1. 구현을 멈추고 사용자에게 먼저 확인: \"원인이 X가 아니라 Y로 보입니다. 문서를 최신화할까요?\"
2. 승인 시 아래 문서를 업데이트:
   - **findings.md** — 원인 분석 수정 (핵심 대상)
   - **tasks.md** — 변경된 원인에 맞게 구현 단계 수정
   - **progress.md** — 방향 변경 사유 및 경위 기록
3. README.md는 증상/요구사항 기술이므로 업데이트 대상 아님

## 세션 이어받기

진행 중인 작업이 있으면:
1. \`docs/\` 에서 상태가 \"진행중\"인 작업의 progress.md를 읽는다
2. 현재 상태를 보고한 후 사용자 승인을 받고 이어서 진행한다

## PR 생성 규칙

PR 생성 시 task 폴더의 문서 5개를 모두 참조하여 작성한다:
- PR 제목에 지라 이슈 번호 포함 (README.md 참조)
- PR 본문: 개요(README) / 변경점(tasks + 변경 파일) / 리뷰 중점사항(findings 기술 결정)
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
# Install
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ ai-skills installer v${VERSION} ━━━${NC}"
echo -e "${CYAN}    Mode: ${MODE} | Scope: ${SCOPE} | Target: ${TARGET_DIR}${NC}"
echo ""

mkdir -p "$TARGET_DIR"

if [[ "$MODE" == "claude" ]]; then
  # ── Claude Code install ──
  if [[ -z "$ONLY" ]]; then
    copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
    copy_dir "$SRC_DIR/agents" "$TARGET_DIR/agents" "agents"
    copy_dir "$SRC_DIR/rules"  "$TARGET_DIR/rules"  "rules"
    merge_claude_md
  else
    copy_dir "$SRC_DIR/$ONLY" "$TARGET_DIR/$ONLY" "$ONLY"
    # skills depend on agents — install agents together
    if [[ "$ONLY" == "skills" ]]; then
      info "Skills reference agents — installing agents as dependency..."
      copy_dir "$SRC_DIR/agents" "$TARGET_DIR/agents" "agents"
    fi
    if [[ "$ONLY" == "skills" || "$ONLY" == "agents" ]]; then
      info "Tip: CLAUDE.md contains rules for ${ONLY}. Run without --only to include it."
    fi
  fi

elif [[ "$MODE" == "cursor" ]]; then
  # ── Cursor install ──
  if [[ -z "$ONLY" || "$ONLY" == "skills" ]]; then
    copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
  fi

  # skills depend on agents — install agents when skills are requested
  if [[ -z "$ONLY" || "$ONLY" == "agents" || "$ONLY" == "skills" ]]; then
    if [[ "$ONLY" == "skills" ]]; then
      info "Skills reference agents — installing agents as dependency..."
    fi
    copy_dir "$SRC_DIR/agents" "$TARGET_DIR/agents" "agents"
  fi

  if [[ -z "$ONLY" || "$ONLY" == "rules" ]]; then
    mkdir -p "$TARGET_DIR/rules"
    local_count=0

    if create_mdc_rule \
      "$SRC_DIR/rules/react-typescript.md" \
      "$TARGET_DIR/rules/react-typescript.mdc" \
      "React + TypeScript 프론트엔드 구현 시 적용" \
      '["*.tsx", "*.ts"]'; then
      ((local_count++))
    fi

    if create_mdc_rule \
      "$SRC_DIR/rules/frontend-design.md" \
      "$TARGET_DIR/rules/frontend-design.mdc" \
      "디자인 레퍼런스 없이 UI를 직접 만들 때 적용" \
      '["*.tsx", "*.css", "*.scss"]'; then
      ((local_count++))
    fi

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
fi

# ─────────────────────────────────────────────
# Browse setup (optional)
# ─────────────────────────────────────────────
BROWSE_SETUP="$TARGET_DIR/skills/browse/setup.sh"
if [[ -f "$BROWSE_SETUP" ]]; then
  echo ""
  echo -e "${CYAN}Browse (headless browser for /qa) detected.${NC}"
  echo -e "  Browse requires bun + Playwright Chromium (~200MB)."
  echo -e "  ${CYAN}1)${NC} Build now"
  echo -e "  ${CYAN}2)${NC} Skip (build later with: bash $BROWSE_SETUP)"
  read -rp "> " browse_choice <&3
  case $browse_choice in
    1)
      info "Building browse..."
      bash "$BROWSE_SETUP" && ok "browse ready!" || warn "browse build failed. Run manually: bash $BROWSE_SETUP"
      ;;
    *)
      info "Skipped. Build later: bash $BROWSE_SETUP"
      ;;
  esac
fi

echo ""
ok "Done! ai-skills installed to ${TARGET_DIR}/"
echo ""
echo -e "  ${CYAN}Update:${NC}  curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --${MODE} --${SCOPE} --update"
echo ""
