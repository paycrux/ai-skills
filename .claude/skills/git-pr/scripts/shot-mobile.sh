#!/usr/bin/env bash
set -euo pipefail

usage="usage: SHOT_SCHEME=<scheme> SHOT_BUNDLE=<bundle-id> [SHOT_PLATFORM=ios|android] shot-mobile.sh <route> <out.png> [wait-sec] [light|dark|both]"

ROUTE="${1:?$usage}"
DEST="${2:?$usage}"
WAIT="${3:-7}"
MODE="${4:-}"

PLATFORM="${SHOT_PLATFORM:-ios}"
SCHEME="${SHOT_SCHEME:?SHOT_SCHEME is not set. $usage}"
BUNDLE="${SHOT_BUNDLE:?SHOT_BUNDLE is not set. $usage}"
ADB="${ADB:-$HOME/Library/Android/sdk/platform-tools/adb}"
METRO_PORT="${METRO_PORT:-8081}"

if [ "$PLATFORM" = "android" ]; then
  [ -x "$ADB" ] || { echo "adb not found: $ADB" >&2; exit 1; }
  "$ADB" get-state >/dev/null 2>&1 || { echo "No Android device connected" >&2; exit 1; }

  setup() { "$ADB" reverse "tcp:${METRO_PORT}" "tcp:${METRO_PORT}" >/dev/null; }
  set_appearance() {
    "$ADB" shell cmd uimode night "$([ "$1" = dark ] && echo yes || echo no)" >/dev/null
  }
  open_route() {
    "$ADB" shell am start -a android.intent.action.VIEW \
      -d "${SCHEME}://${ROUTE}" "$BUNDLE" >/dev/null 2>&1
  }
  capture_raw() {
    "$ADB" shell screencap -p /sdcard/_shot.png 2>/dev/null
    "$ADB" pull /sdcard/_shot.png "$1" >/dev/null 2>&1
    "$ADB" shell rm /sdcard/_shot.png 2>/dev/null
  }
elif [ "$PLATFORM" = "ios" ]; then
  SIM=$(xcrun simctl list devices booted | grep -o '[0-9A-F-]\{36\}' | head -1 || true)
  [ -n "$SIM" ] || { echo "No booted iOS simulator" >&2; exit 1; }

  setup() {
    xcrun simctl launch "$SIM" "$BUNDLE" >/dev/null 2>&1 \
      || { echo "Failed to launch $BUNDLE. Check that it is installed on the simulator" >&2; exit 1; }
  }
  set_appearance() { xcrun simctl ui "$SIM" appearance "$1" >/dev/null; }
  open_route() { xcrun simctl openurl "$SIM" "${SCHEME}://${ROUTE}"; }
  capture_raw() { xcrun simctl io "$SIM" screenshot "$1" >/dev/null 2>&1; }
else
  echo "SHOT_PLATFORM must be ios or android" >&2
  exit 1
fi

capture() {
  local out="$1"
  open_route
  sleep "$WAIT"
  capture_raw "$out"
  sips -Z 800 "$out" --out "${out%.png}-s.png" >/dev/null
  echo "$out"
}

setup
mkdir -p "$(dirname "$DEST")"

case "$MODE" in
  '')
    capture "$DEST"
    ;;
  light | dark)
    set_appearance "$MODE"
    sleep 3
    capture "$DEST"
    ;;
  both)
    LIGHT="${DEST%.png}_light.png"
    DARK="${DEST%.png}_dark.png"

    set_appearance light
    sleep 3
    capture "$LIGHT"

    set_appearance dark
    sleep 3
    capture "$DARK"

    if cmp -s "$LIGHT" "$DARK"; then
      echo "warning: light and dark captures are identical. Check that the app's color setting follows the system" >&2
    fi
    ;;
  *)
    echo "4th argument must be light | dark | both" >&2
    exit 1
    ;;
esac
