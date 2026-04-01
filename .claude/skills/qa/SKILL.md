---
name: qa
description: "task-plan 문서 기반으로 browse(헤드리스 브라우저)를 사용해 구현 결과를 검증. 버그 리포트 작성 후 바로 수정 여부를 확인하여 /implement로 연결."
argument-hint: "<task-folder-name or URL>"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Skill
---

# /qa — 구현 검증 워크플로우

task-plan 문서를 기반으로 browse 헤드리스 브라우저를 사용해 구현 결과를 실제 사용자 관점에서 검증합니다.
버그를 발견하면 리포트를 작성하고, 즉시 수정할지 사용자에게 확인합니다.

## Argument Parsing

- `/qa <task-folder-name>` — `docs/plans/<task-folder-name>/` 기준
- `/qa <url>` — URL 직접 지정
- `/qa` (인자 없음) — `docs/plans/`에서 상태가 "진행중"인 task 자동 탐지

## Step 1: Browse 설정

```bash
B=""
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -n "$_ROOT" ] && [ -x "$_ROOT/.claude/skills/browse/dist/browse" ] && B="$_ROOT/.claude/skills/browse/dist/browse"
[ -z "$B" ] && [ -x "$HOME/.claude/skills/browse/dist/browse" ] && B="$HOME/.claude/skills/browse/dist/browse"
if [ -x "$B" ]; then
  echo "READY: $B"
else
  echo "NEEDS_SETUP"
fi
```

**NEEDS_SETUP인 경우:**
1. 사용자에게 알림: "browse 바이너리 빌드가 필요합니다 (~30초). 진행할까요?"
2. 승인 후: `bash ~/.claude/skills/browse/setup.sh` (또는 프로젝트 로컬 경로)

## Step 2: 테스트 범위 결정

### 2-1. Task-plan 문서 로드

인자로 task-folder가 주어진 경우, 다음 파일을 병렬 Read:

| 파일 | 용도 |
|------|------|
| `README.md` | 목표, 범위 |
| `spec.md` | 기능 흐름, 상태 정의, 엣지 케이스 |
| `tasks.md` | Phase별 구현 체크리스트 |
| `ui-spec.md` | (있으면) 화면 구조, 컴포넌트 구성 |
| `progress.md` | 현재 진행 상태 |

### 2-2. 테스트 대상 파악

task-plan 문서가 있는 경우:
1. `spec.md`에서 기능 흐름 추출 → 테스트 시나리오로 변환
2. `ui-spec.md`에서 화면/컴포넌트 목록 → 검증 대상 페이지
3. `tasks.md`에서 완료된 Phase의 변경 파일 → 영향받는 라우트 파악

task-plan 문서가 없는 경우 (URL만 주어진 경우):
1. git diff로 변경 파일 분석
2. 변경된 파일에서 영향받는 페이지/라우트 식별
3. 해당 페이지에 대해 탐색적 테스트

### 2-3. 앱 URL 확인

URL이 주어지지 않은 경우 자동 탐지:
```bash
$B goto http://localhost:3000 2>/dev/null && echo "Found :3000" || \
$B goto http://localhost:5173 2>/dev/null && echo "Found :5173" || \
$B goto http://localhost:4000 2>/dev/null && echo "Found :4000" || \
$B goto http://localhost:8080 2>/dev/null && echo "Found :8080"
```

못 찾으면 사용자에게 URL 요청.

## Step 3: QA 실행

### 3-1. 초기 탐색

```bash
$B goto <target-url>
$B snapshot -i -a -o /tmp/qa-initial.png
$B console --errors
$B links
```

Read 도구로 스크린샷을 사용자에게 보여준다.

### 3-2. 시나리오별 테스트

spec.md (또는 변경 범위)에서 도출한 각 시나리오에 대해:

1. **페이지 이동** — `$B goto <page-url>`
2. **스냅샷** — `$B snapshot -i -a -o /tmp/qa-{page}.png`
3. **인터랙션 테스트** — 버튼 클릭, 폼 입력, 네비게이션
4. **상태 검증** — `$B is visible`, `$B js`, `$B snapshot -D`
5. **콘솔 확인** — `$B console --errors`
6. **반응형** — 필요 시 `$B responsive /tmp/qa-{page}`

**테스트 우선순위:**
- 핵심 기능 (spec.md의 주요 플로우) > 엣지 케이스 > 시각적 검증

### 3-3. 이슈 기록

버그 발견 시 즉시 기록. 각 이슈에 대해:

1. 스크린샷 증거 촬영
2. 재현 단계 작성
3. 심각도 분류:
   - **Critical** — 핵심 기능 불가, 데이터 손실
   - **High** — 주요 기능 장애, 워크어라운드 존재
   - **Medium** — 부분 기능 장애, UX 문제
   - **Low** — 시각적 결함, 미세 문제

## Step 4: 리포트 작성

`docs/plans/<task-name>/qa-report.md`에 결과 저장:

```markdown
# QA Report: {task-name}

**날짜:** {YYYY-MM-DD}
**대상 URL:** {url}
**테스트 범위:** {spec.md 기반 / diff 기반 / 전체 탐색}

## 요약

| 심각도 | 건수 |
|--------|------|
| Critical | N |
| High | N |
| Medium | N |
| Low | N |

## 테스트 시나리오 결과

### 시나리오 1: {제목}
- **상태:** PASS / FAIL
- **설명:** {테스트 내용}
- **증거:** ![스크린샷](경로)

## 발견된 이슈

### ISSUE-001: {제목}
- **심각도:** {Critical/High/Medium/Low}
- **재현 단계:**
  1. {step}
  2. {step}
- **기대 결과:** {expected}
- **실제 결과:** {actual}
- **스크린샷:** {경로}

## 결론

{전체 상태 요약}
```

## Step 5: 수정 연결

리포트 작성 완료 후, 이슈가 있다면 사용자에게 확인:

```
QA 검증이 완료되었습니다.

발견된 이슈:
- Critical: N건
- High: N건
- Medium: N건
- Low: N건

바로 수정을 진행할까요?
  A) 전체 수정 — Critical부터 순서대로 모두 수정
  B) Critical/High만 수정
  C) 수정하지 않음 — 리포트만 유지
```

### 수정 진행 시

사용자가 A 또는 B를 선택하면:

1. qa-report.md의 이슈 목록을 기반으로 **수정 작업용 tasks 구성**
2. `/implement` 스킬을 호출하여 수정 실행:
   - task-plan이 있는 경우: qa-report.md의 이슈를 tasks.md에 "QA Fix Phase"로 추가 후 `/implement` 실행
   - task-plan이 없는 경우: 직접 적절한 에이전트(implement-engineering / implement-react)를 실행

3. 수정 완료 후 해당 이슈에 대해 재검증:
   ```bash
   $B goto <affected-url>
   $B snapshot -D
   $B console --errors
   ```

4. qa-report.md 업데이트: 이슈 상태를 `FIXED` / `VERIFIED`로 변경

## 규칙

- **사용자 관점으로 테스트** — 소스 코드를 보고 테스트하지 말 것. 실제 사용자처럼 클릭하고 입력
- **증거 필수** — 모든 이슈에 스크린샷 첨부. 재현 불가능한 이슈는 보고하지 않음
- **스크린샷 보여주기** — 촬영 후 반드시 Read 도구로 사용자에게 보여줄 것
- **콘솔 확인 필수** — 모든 인터랙션 후 `$B console --errors` 체크
- **비밀정보 포함 금지** — 비밀번호 등은 `[REDACTED]`로 표기
- **browse 사용 거부 금지** — /qa 호출 시 반드시 브라우저 기반 테스트 수행
- 사용자와 한국어로 소통
