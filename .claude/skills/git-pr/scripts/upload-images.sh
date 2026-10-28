#!/usr/bin/env bash
set -euo pipefail

usage="usage: upload-images.sh <owner/repo> <issue-or-pr-number> <image> [image...]"

REPO="${1:?$usage}"
ISSUE="${2:?$usage}"
shift 2
[ "$#" -gt 0 ] || { echo "$usage" >&2; exit 1; }

SESSION="${GH_UPLOAD_SESSION:-gh-attach}"
PW=(playwright-cli --session "$SESSION")

for cmd in playwright-cli jq curl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd is required" >&2; exit 1; }
done

images=()
for img in "$@"; do
  [ -f "$img" ] || { echo "Image not found: $img" >&2; exit 1; }
  images+=("$(cd "$(dirname "$img")" && pwd -P)/$(basename "$img")")
done

# playwright-cli only lets the page touch files under the directory it was started from
cd "$(dirname "${images[0]}")"

pw_result() {
  "${PW[@]}" eval "$1" 2>/dev/null | sed -n '/^### Result$/{n;p;q;}'
}

"${PW[@]}" open --persistent "https://github.com/$REPO/issues/$ISSUE" >/dev/null 2>&1
sleep 3

if [ "$(pw_result "() => !!document.querySelector('file-attachment')")" != "true" ]; then
  echo "Browser session '$SESSION' is not logged in to GitHub (no upload form on the page)." >&2
  echo "Log in once: playwright-cli --session $SESSION open --persistent --headed https://github.com/login" >&2
  "${PW[@]}" close >/dev/null 2>&1 || true
  exit 3
fi

for img in "${images[@]}"; do
  name="$(basename "$img")"
  size="$(wc -c < "$img" | tr -d ' ')"
  case "${name##*.}" in
    png) type="image/png" ;;
    jpg|jpeg) type="image/jpeg" ;;
    gif) type="image/gif" ;;
    webp) type="image/webp" ;;
    *) type="application/octet-stream" ;;
  esac
  js_name="$(jq -Rn --arg v "$name" '$v')"

  policy_js="async () => {
    const file = new File([new ArrayBuffer($size)], $js_name, { type: '$type' });
    const origFetch = window.fetch;
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    let policy = null;
    window.fetch = async function (input) {
      const url = typeof input === 'string' ? input : (input instanceof Request ? input.url : '');
      const res = await origFetch.apply(this, arguments);
      if (url.includes('upload/policies')) policy = await res.clone().json();
      return res;
    };
    XMLHttpRequest.prototype.open = function (method, url) { this.__url = String(url); return origOpen.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
      if (this.__url && !this.__url.startsWith(location.origin)) return;
      return origSend.apply(this, arguments);
    };
    const dt = new DataTransfer();
    dt.items.add(file);
    document.querySelector('file-attachment').attach(dt);
    for (let i = 0; i < 30 && !policy; i++) await new Promise((r) => setTimeout(r, 200));
    window.fetch = origFetch;
    XMLHttpRequest.prototype.open = origOpen;
    XMLHttpRequest.prototype.send = origSend;
    return JSON.stringify(policy);
  }"

  policy="$(pw_result "$policy_js" | jq -r '.')"
  upload_url="$(echo "$policy" | jq -r '.upload_url // empty')"
  if [ -z "$upload_url" ]; then
    echo "Failed to get upload policy for: $img" >&2
    exit 1
  fi

  curl_args=(-s -o /dev/null -w '%{http_code}' -X POST "$upload_url")
  while IFS= read -r field; do
    curl_args+=(-F "$field")
  done < <(echo "$policy" | jq -r '.form | to_entries[] | "\(.key)=\(.value)"')
  curl_args+=(-F "file=@$img;type=$type")

  status="$(curl "${curl_args[@]}")"
  case "$status" in
    2*) ;;
    *) echo "Storage upload failed ($status) for: $img" >&2; exit 1 ;;
  esac

  finalize_url="$(echo "$policy" | jq -r '.asset_upload_url')"
  finalize_token="$(echo "$policy" | jq -r '.asset_upload_authenticity_token')"
  finalize_js="async () => {
    const body = new FormData();
    body.append('authenticity_token', $(jq -Rn --arg v "$finalize_token" '$v'));
    const res = await fetch($(jq -Rn --arg v "$finalize_url" '$v'), {
      method: 'PUT',
      body,
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
    });
    return res.status;
  }"
  final_status="$(pw_result "$finalize_js")"
  case "$final_status" in
    2*) ;;
    *) echo "Asset finalize failed ($final_status) for: $img" >&2; exit 1 ;;
  esac

  echo "$policy" | jq -r '.asset.href'

  "${PW[@]}" reload >/dev/null 2>&1
  sleep 2
done

"${PW[@]}" close >/dev/null 2>&1 || true
