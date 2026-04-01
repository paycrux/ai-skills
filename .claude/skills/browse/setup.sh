#!/usr/bin/env bash
# ai-skills browse setup — build browser binary + install Chromium
set -e

BROWSE_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$BROWSE_DIR/dist"
BROWSE_BIN="$DIST_DIR/browse"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[browse]${NC} $1"; }
ok()    { echo -e "${GREEN}[browse]${NC} $1"; }
error() { echo -e "${RED}[browse]${NC} $1"; exit 1; }

# ─── Check bun ────────────────────────────────────────────
if ! command -v bun >/dev/null 2>&1; then
  echo ""
  echo -e "${CYAN}bun이 설치되어 있지 않습니다.${NC}"
  echo -e "browse 빌드에 bun이 필요합니다."
  echo ""
  echo -e "  ${CYAN}1)${NC} 자동 설치 (curl -fsSL https://bun.sh/install | bash)"
  echo -e "  ${CYAN}2)${NC} 취소 — 직접 설치 후 다시 실행"
  read -rp "> " bun_choice
  case $bun_choice in
    1)
      info "bun 설치 중..."
      curl -fsSL https://bun.sh/install | bash
      # bun을 현재 세션 PATH에 추가
      export BUN_INSTALL="$HOME/.bun"
      export PATH="$BUN_INSTALL/bin:$PATH"
      if ! command -v bun >/dev/null 2>&1; then
        error "bun 설치 실패. 수동으로 설치해주세요: https://bun.sh"
      fi
      ok "bun 설치 완료: $(bun --version)"
      ;;
    *)
      error "bun 설치 후 다시 실행해주세요: curl -fsSL https://bun.sh/install | bash"
      ;;
  esac
fi

# ─── Smart rebuild detection ─────────────────────────────
NEEDS_BUILD=0

if [ ! -x "$BROWSE_BIN" ]; then
  NEEDS_BUILD=1
elif [ "$BROWSE_DIR/package.json" -nt "$BROWSE_BIN" ]; then
  NEEDS_BUILD=1
else
  # Check if any source file is newer than the binary
  for src in "$BROWSE_DIR"/src/*.ts; do
    if [ "$src" -nt "$BROWSE_BIN" ]; then
      NEEDS_BUILD=1
      break
    fi
  done
fi

if [ "$NEEDS_BUILD" -eq 0 ]; then
  ok "browse binary is up to date: $BROWSE_BIN"
  exit 0
fi

# ─── Install dependencies ────────────────────────────────
info "Installing dependencies..."
cd "$BROWSE_DIR"
bun install --frozen-lockfile 2>/dev/null || bun install

# ─── Build binary ─────────────────────────────────────────
info "Building browse binary..."
mkdir -p "$DIST_DIR"
bun build --compile src/cli.ts --outfile "$BROWSE_BIN"
chmod +x "$BROWSE_BIN"

# ─── Install Chromium ─────────────────────────────────────
info "Installing Chromium browser..."
cd "$BROWSE_DIR"
bunx playwright install chromium

ok "browse ready: $BROWSE_BIN"
