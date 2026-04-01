#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────
# ai-skills installer
# https://github.com/paycrux/ai-skills
# ─────────────────────────────────────────────

REPO_URL="https://github.com/paycrux/ai-skills.git"
MARKER_START="<!-- AI-SKILLS:START -->"
MARKER_END="<!-- AI-SKILLS:END -->"
VERSION="1.0.0"

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

while [[ $# -gt 0 ]]; do
  case $1 in
    --only)
      ONLY="$2"
      shift 2
      ;;
    --update)
      UPDATE=true
      shift
      ;;
    --help|-h)
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --only <type>   Install specific type only: skills, agents, rules"
      echo "  --update        Update existing installation (safe merge)"
      echo "  -h, --help      Show this help"
      echo ""
      echo "Examples:"
      echo "  bash install.sh                  # Full install"
      echo "  bash install.sh --only skills    # Skills only"
      echo "  bash install.sh --only agents    # Agents only"
      echo "  bash install.sh --update         # Update ai-skills files only"
      exit 0
      ;;
    *)
      error "Unknown option: $1 (use --help)"
      ;;
  esac
done

# Validate --only value
if [[ -n "$ONLY" ]] && [[ "$ONLY" != "skills" && "$ONLY" != "agents" && "$ONLY" != "rules" ]]; then
  error "--only must be one of: skills, agents, rules"
fi

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────
TARGET_DIR="$(pwd)/.claude"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

info "Cloning ai-skills repository..."
git clone --depth 1 --quiet "$REPO_URL" "$TMP_DIR"
SRC_DIR="$TMP_DIR/.claude"

if [[ ! -d "$SRC_DIR" ]]; then
  error ".claude directory not found in repository"
fi

# ─────────────────────────────────────────────
# Helper: copy files safely (no overwrite of user files)
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
      # File exists — check if it's from ai-skills (has marker or is identical)
      if $UPDATE; then
        # Update mode: overwrite ai-skills files
        cp "$file" "$dest_file"
        ((count++))
      else
        # Fresh install: skip existing files
        warn "Skipped (already exists): .claude/${label}/${rel}"
        ((skipped++))
      fi
    else
      cp "$file" "$dest_file"
      ((count++))
    fi
  done < <(find "$src" -type f -print0)

  ok "$label: ${count} files installed"
  if [[ $skipped -gt 0 ]]; then
    warn "$label: ${skipped} files skipped (already exist, use --update to overwrite)"
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
    # No existing file — create with markers
    echo "$marked_content" > "$dest_file"
    ok "CLAUDE.md created"
    return
  fi

  # File exists — check for markers
  if grep -q "$MARKER_START" "$dest_file"; then
    # Markers exist — replace between them
    local before after
    before=$(sed -n "1,/${MARKER_START}/{ /${MARKER_START}/!p; }" "$dest_file")
    after=$(sed -n "/${MARKER_END}/,\${ /${MARKER_END}/!p; }" "$dest_file")

    {
      [[ -n "$before" ]] && echo "$before"
      echo "$marked_content"
      [[ -n "$after" ]] && echo "$after"
    } > "$dest_file"
    ok "CLAUDE.md updated (ai-skills section replaced)"
  else
    # No markers — prepend with markers, keep existing content
    local existing
    existing=$(cat "$dest_file")
    {
      echo "$marked_content"
      echo ""
      echo "$existing"
    } > "$dest_file"
    ok "CLAUDE.md merged (ai-skills section prepended)"
  fi
}

# ─────────────────────────────────────────────
# Install
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ ai-skills installer v${VERSION} ━━━${NC}"
echo ""

mkdir -p "$TARGET_DIR"

if [[ -z "$ONLY" ]]; then
  # Full install
  copy_dir "$SRC_DIR/skills" "$TARGET_DIR/skills" "skills"
  copy_dir "$SRC_DIR/agents" "$TARGET_DIR/agents" "agents"
  copy_dir "$SRC_DIR/rules"  "$TARGET_DIR/rules"  "rules"
  merge_claude_md
else
  # Selective install
  copy_dir "$SRC_DIR/$ONLY" "$TARGET_DIR/$ONLY" "$ONLY"

  if [[ "$ONLY" == "skills" || "$ONLY" == "agents" ]]; then
    info "Tip: CLAUDE.md contains rules for ${ONLY}. Run without --only to include it."
  fi
fi

# Copy Cursor setup guide to project root if not exists
if [[ -z "$ONLY" ]] && [[ -f "$TMP_DIR/CURSOR_SETUP_GUIDE.md" ]]; then
  if [[ ! -f "$(pwd)/CURSOR_SETUP_GUIDE.md" ]]; then
    cp "$TMP_DIR/CURSOR_SETUP_GUIDE.md" "$(pwd)/CURSOR_SETUP_GUIDE.md"
    ok "CURSOR_SETUP_GUIDE.md copied to project root"
  fi
fi

echo ""
ok "Done! ai-skills installed to .claude/"
echo ""
echo -e "  ${CYAN}Update later:${NC}  bash <(curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh) --update"
echo -e "  ${CYAN}Or from clone:${NC}  bash path/to/ai-skills/install.sh --update"
echo ""
