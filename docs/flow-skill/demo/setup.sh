#!/usr/bin/env bash
# Builds a throwaway repository for a live /flow demo. Re-run it to reset the demo.
#   bash docs/flow-skill/demo/setup.sh [target dir, default ~/flow-demo]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/flow-demo}"

if [ -e "$TARGET" ]; then
  if [ ! -f "$TARGET/.flow-demo" ]; then
    echo "refusing: $TARGET exists and was not made by this script (no .flow-demo marker)" >&2
    exit 1
  fi
  rm -rf "$TARGET"
fi

mkdir -p "$TARGET"
cp -R "$HERE/app/." "$TARGET/"
cp -R "$HERE/inputs" "$TARGET/demo-inputs"
cp "$HERE/DEMO.md" "$TARGET/DEMO.md"
touch "$TARGET/.flow-demo"

cd "$TARGET"
FLOW="$HOME/.claude/skills/flow/scripts/flow.py"
[ -f "$FLOW" ] || FLOW="$HERE/../../../.claude/skills/flow/scripts/flow.py"
git init -q -b main
python3 "$FLOW" build docs >/dev/null
git add -A
git -c user.name="flow demo" -c user.email="demo@example.com" commit -q -m "chore: 시연용 선물하기 앱"

echo "demo repo ready: $TARGET"
echo "next: cd $TARGET && claude   (prompts are in DEMO.md)"
