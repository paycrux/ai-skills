# Screenshots for `## 구현 화면`

Capture Before/After screens for the PR body, upload them, and fill the table. Read this when the
PR phase reaches **Capture screenshots**.

## Contents

- [Principle](#principle)
- [1. Decide what to capture](#1-decide-what-to-capture)
- [2. Check the capture environment](#2-check-the-capture-environment)
- [3. Capture After](#3-capture-after)
- [4. Capture Before](#4-capture-before)
- [5. Verify every image](#5-verify-every-image)
- [6. Fill the table](#6-fill-the-table)
- [7. Upload and publish](#7-upload-and-publish)

## Principle

**Fill every cell you can.** A cell stays blank only when that capture actually failed, and every
blank cell gets a one-line reason in the conversation. Never write `없음` in a cell.

Shots live outside the repository and are never committed:

```bash
SHOTS="${TMPDIR:-/tmp}/git-pr-shots/$(echo "{HEAD_BRANCH}" | tr '/' '-')"
mkdir -p "$SHOTS"
```

File names: `{screen}_{before|after}_{ios|aos|web}[_light|_dark].png`, where `{screen}` is a short
ASCII slug.

## 1. Decide what to capture

### Platforms

Read `package.json` at the repository root:

| Dependency | Platform |
|---|---|
| `react-native` or `expo` | mobile — iOS and Android |
| `next`, `vite`, `react-dom` without `react-native` | web |

A monorepo can have both; decide per screen by the package the changed file belongs to.

### Screens

From `git diff origin/{PR_BASE}..{HEAD_BRANCH} --name-only`, list the screens whose rendering the
diff changes: route files directly (`app/**`, `pages/**`), and for a changed component, the routes
that render it (grep for its importers). Show the list in Korean, one line per screen —
`{화면 이름} — {route 또는 URL} — {플랫폼}` — and call `AskUserQuestion`:

- prompt: `"이 화면들을 촬영할까요?"`
- options: `["이대로 촬영", "수정할게요 — 화면 추가·제외 또는 경로 수정"]`

A screen that only appears under a server state or a mid-flow step a URL cannot reach (a modal
after a failed payment, a remote-config switch) cannot be opened by a deep link. Mark it
`촬영 불가 — {이유}` in the list and leave its cells blank; do not patch app code to reach it.

### Before

Unless `--shots` already decided it, call `AskUserQuestion`:

- prompt: `"Before 화면도 찍을까요? base 브랜치 코드로 잠시 전환했다가 돌아옵니다."`
- options: `["Before + After 모두 찍기", "After만 찍기 — Before 칸은 비워 둠"]`

## 2. Check the capture environment

### Mobile

`scripts/shot-mobile.sh` needs the app's deep link scheme and bundle id. The values are stored per
clone in the git common directory so every worktree shares them and nothing gets committed:

```bash
SHOT_ENV="$(git rev-parse --git-common-dir)/git-pr-shot.env"
[ -f "$SHOT_ENV" ] && cat "$SHOT_ENV"
```

If the file is missing, read `scheme`, `ios.bundleIdentifier`, and `android.package` from
`app.json` / `app.config.*`. When the config is dynamic (per-environment variants) or the values
disagree with the installed app, ask the user in plain conversation. Find the Metro port with
`lsof -nP -iTCP -sTCP:LISTEN | grep node`. Then write:

```bash
SHOT_SCHEME=<scheme>
SHOT_BUNDLE_IOS=<ios bundle id>
SHOT_BUNDLE_AOS=<android package>
METRO_PORT=<port>
```

Preconditions, checked per platform — a failed one drops that platform's rows, it does not stop
the other platform:

| Platform | Check | On failure |
|---|---|---|
| iOS | `xcrun simctl list devices booted` shows a device, the dev build is installed, Metro is running | Tell the user what is missing (`npm run ios` or similar) |
| Android | `adb get-state` succeeds, the dev build is installed | Same |

Run the script with the env file loaded:

```bash
set -a; . "$SHOT_ENV"; set +a
SHOT_PLATFORM=ios     SHOT_BUNDLE="$SHOT_BUNDLE_IOS" "${CLAUDE_SKILL_DIR}/scripts/shot-mobile.sh" <route> "$SHOTS/<file>.png" [wait] [light|dark|both]
SHOT_PLATFORM=android SHOT_BUNDLE="$SHOT_BUNDLE_AOS" "${CLAUDE_SKILL_DIR}/scripts/shot-mobile.sh" <route> "$SHOTS/<file>.png" [wait] [light|dark|both]
```

- The app must already be running. A cold start on iOS opens the dev client launcher and drops
  the route.
- Light/dark switching follows the OS setting, so it only works when the app's own color setting
  follows the system. If the script warns that both captures are identical, ask the user to set
  the app to follow the system and capture again.
- Never automate taps with `System Events click at` — it uses global screen coordinates and
  clicks other windows.

### Web

Use the `browse` skill (its Setup block gives `$B`). Find the dev server with
`lsof -nP -iTCP -sTCP:LISTEN`; if none is running for this repository, ask the user to start it or
skip web. Log in per the browse rules when the screen requires it.

Viewport: `$B viewport 1440x900`, or `$B viewport 390x844` when the project is mobile-first
(a fixed max-width app shell). Use the same viewport for Before and After.

Dark mode: capture a dark column only when the project has one (`darkMode` in the Tailwind config,
`next-themes`, a theme toggle). Switch it the way the app does — its toggle, or the storage key the
theme provider reads followed by a reload.

## 3. Capture After

Capture After first, on `HEAD_BRANCH` as it is now, so a failed Before still leaves the After
column filled.

| Platform | Command |
|---|---|
| Mobile | `shot-mobile.sh <route> "$SHOTS/{screen}_after_{ios\|aos}.png" 7 both` |
| Web | `$B goto <url>` → `$B screenshot "$SHOTS/{screen}_after_web.png"` (and `_dark` when applicable) |

## 4. Capture Before

Skip this section when the user chose `After만 찍기`.

Skip Before for a platform, and say why, when:

- `git status --porcelain --untracked-files=no` is not empty — switching would carry or block
  uncommitted changes
- mobile: the diff touches `ios/`, `android/`, `plugins/`, `app.json`, `app.config.*`,
  `package.json`, or a lockfile — a JS reload cannot bring the base's native code back
- web: the diff touches `package.json` or a lockfile

Then:

```bash
git switch --detach origin/{PR_BASE}
```

Wait for the dev server or Metro to pick up the change (web: reload the page; mobile: pass a
longer wait, e.g. `12`). Capture each screen in light only:

| Platform | Command |
|---|---|
| Mobile | `shot-mobile.sh <route> "$SHOTS/{screen}_before_{ios\|aos}.png" 12 light` |
| Web | `$B goto <url>` → `$B screenshot "$SHOTS/{screen}_before_web.png"` |

A screen the base branch does not have is a new screen: its Before cell reads `신규 화면`.

**Always switch back, including after a failed capture:**

```bash
git switch {HEAD_BRANCH}
git branch --show-current
```

Confirm the printed branch is `HEAD_BRANCH` before doing anything else, then reload once so the app
is back on the branch's code.

## 5. Verify every image

Open each capture with the Read tool — for mobile the `-s.png` thumbnail. The script reports
success even when it captured a splash screen, an error overlay, or the wrong route. For each
wrong capture, retry once with a longer wait; if it is still wrong, delete the file and leave the
cell blank with the reason.

## 6. Fill the table

Rows are `{플랫폼} · {화면}`. Mobile and web use separate tables when both exist.

Mobile:

```markdown
| | Before | After (light) | After (dark) |
| :-- | :--: | :--: | :--: |
| **iOS · {화면}** | <img src="{path}" width="200" /> | <img src="{path}" width="200" /> | <img src="{path}" width="200" /> |
| **AOS · {화면}** | <img src="{path}" width="200" /> | <img src="{path}" width="200" /> | <img src="{path}" width="200" /> |
```

Web (drop the dark column when the project has no dark mode):

```markdown
| | Before | After | After (dark) |
| :-- | :--: | :--: | :--: |
| **{화면}** | <img src="{path}" width="400" /> | <img src="{path}" width="400" /> | <img src="{path}" width="400" /> |
```

Until upload, `{path}` is the capture's absolute local path — the preview file renders it in the
editor, and step 7 replaces each path with its uploaded URL. For mobile, reference the `-s.png`
thumbnail; it is enough for a 200px cell and uploads faster.

## 7. Upload and publish

`gh attach` needs an existing issue or PR page to upload through, so the PR is created as a draft
first and published only after the images are in. Reviewers never see an imageless body.

1. Create the primary PR with `--draft` and the body file that still holds local paths. Take the
   PR number from the returned URL.
2. Upload every image referenced in the body, in the order they appear:

   ```bash
   gh attach --issue {PR_NO} --url-only --image <path1> --image <path2> ...
   ```

   It prints one URL per line, in argument order.
3. Replace each local path in `.pr-body.tmp.md` with its URL, then check that no local path is left:

   ```bash
   grep -c "$SHOTS" "{REPO_ROOT}/.pr-body.tmp.md"
   ```

   The count must be `0`.
4. Publish:

   ```bash
   gh pr edit {PR_NO} --body-file "{REPO_ROOT}/.pr-body.tmp.md"
   gh pr ready {PR_NO}
   ```

5. Create any secondary PR afterwards, not as a draft, from the same finished body file.

If the upload fails, leave the PR as a draft, report the error in Korean, and call
`AskUserQuestion`:

- prompt: `"이미지 업로드에 실패했어요. 어떻게 할까요?"`
- options: `["다시 시도", "이미지 칸을 비우고 공개", "draft로 두기 — 직접 처리할게요"]`

For `이미지 칸을 비우고 공개`, replace every `<img ...>` still holding a local path with an empty
cell before `gh pr edit` and `gh pr ready`.

Delete `$SHOTS` only after the PR is published with every image in place.
