# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.1] - 2026-07-07

### Changed

- `install.sh --update`: 변경된 파일마다 diff를 보여주고 overwrite/skip/show-diff를 묻던 프롬프트를 제거 — `--update` 실행 시 변경된 파일은 항상 최신 버전으로 자동 반영
- `install.sh`: 설치 완료 시 물어보던 "Browse 지금 빌드할까요?" 프롬프트 제거 — browse 바이너리는 `/qa`, `/browse` 스킬이 실제로 처음 사용될 때 없으면 그때 빌드 여부를 확인 (`.claude/skills/qa/SKILL.md`, `.claude/skills/browse/SKILL.md`의 기존 Setup 단계)

## [0.6.0] - 2026-07-07

### Added

- `create-prd` 스킬 추가 — 큰 마크다운 문서(로컬 파일 또는 Notion URL/page ID)를 H2 제목 기준으로 분할해 `docs/<name>/prd/`에 섹션별 파일 + 목차가 있는 `0-overview.md`를 생성
- `notion-do` 스킬 추가 — Notion 링크를 `notion-cli`로 읽어와 요약/추출/질문답변/변환/번역 등 사용자가 요청하는 임의의 작업을 수행하는 범용 Notion 액션 스킬
- `install.sh`: 실행 초반에 `/dev/tty`를 무조건 열어보던 로직을 제거하고, 실제 프롬프트가 필요한 시점에만 지연 바인딩하는 `ensure_tty()`로 교체. `--claude --global --update`처럼 필요한 플래그가 모두 주어진 비대화형 실행(CI, 파이프 등)은 더 이상 터미널을 요구하지 않음

### Fixed

- `install.sh`: 컨트롤링 터미널이 없는 환경에서 `error()`가 정의되기도 전에 호출되어 알아보기 힘든 `command not found` 오류로 죽던 문제 수정 — 이제 각 프롬프트 지점에서 안전한 기본값으로 대체(기존 설치 감지 시 fresh install, 파일 변경 diff 시 skip, browse 빌드 시 skip)하고 상황을 안내하는 경고를 출력
- `qa-guide`: QA 가이드를 별도 `qa-guide.md` 파일 대신 `tasks.md` 안의 `## QA 가이드` 섹션으로 작성하도록 변경 — task-plan 산출물을 `tasks.md` 하나로 유지. `tasks.md` 헤더에 Jira 이슈 키가 있으면 `acli`로 해당 섹션을 이슈 설명에도 동기화(acli 미설치/미로그인 시 스킵하고 안내만 표시)

## [0.5.2] - 2026-07-07

### Added

- `ai-skills install` 명령 추가 — 아직 설치하지 않은 에디터(claude/cursor/codex)를 추가로 설치할 때 사용. `~/.ai-skills/repo`를 pull한 뒤 `install.sh`에 인자를 그대로 위임하며, 옵션 없이 실행하면 `install.sh` 자체의 에디터/범위 대화형 선택으로 진입

### Changed

- `ai-skills update`: 기록된 설치 대상이 1개뿐이어도 항상 어떤 것을 업데이트할지 확인하는 대화형 프롬프트를 표시하도록 변경 (기존엔 대상이 1개면 프롬프트 없이 바로 진행)
- `README.md`에 `ai-skills install` 사용법 추가, `ai-skills update` 설명 문구 수정

## [0.5.1] - 2026-07-07

### Added

- `ai-skills update`: 기록된 설치 대상이 둘 이상이면 어떤 것을 업데이트할지 번호로 고르는 대화형 프롬프트 추가 (기존엔 항상 전부 갱신)
- `ai-skills update`에 `--claude` / `--cursor` / `--codex` 필터 플래그 추가 — 지정한 대상만 업데이트
- `ai-skills update --all` 추가 — 프롬프트 없이 기록된 모든 대상 업데이트 (기존 동작과 동일)
- `README.md` "업데이트 (`ai-skills` CLI)" 섹션에 대화형 프롬프트 예시와 필터 플래그 표 추가

## [0.5.0] - 2026-07-07

### Added

- **Codex 지원** (`install.sh --codex`) — Cursor 미러링 방식으로 `~/.codex/`(전역) 또는 `./.codex/`(프로젝트)에 skills·rules 복사, Codex가 읽는 `AGENTS.md`(전역 `~/.codex/AGENTS.md` / 프로젝트 루트)에 스킬 참조 병합. rules는 `.mdc`가 아닌 일반 `.md`로 설치. 대화형 메뉴·`--help`·예시에 Codex 추가. `ai-skills update`도 기록된 codex 대상을 동일하게 순회 갱신
- `ai-skills` 전역 CLI 추가 (`bin/ai-skills`) — `curl | bash` 전체 재다운로드 없이 한 줄로 업데이트
  - `ai-skills update`: `~/.ai-skills/repo`를 pull한 뒤 `~/.ai-skills/installs.json`에 기록된 모든 설치 대상을 저장된 mode/scope로 `install.sh --update` 재실행 (project scope는 기록된 `target_dir` 상위에서 실행해 타깃을 정확히 복원)
  - `ai-skills version`: 로컬 설치 버전과 원격 최신 버전(`origin/HEAD`)을 비교해 출력
  - 에이전트 훅(Claude SessionStart / Cursor sessionStart / Codex hooks.json)에 의존하지 않는 순수 셸 도구 — 어떤 에이전트를 쓰든 동일하게 동작
- `install.sh`: 비-`--local` 설치 시 저장소를 `~/.ai-skills/repo`에 **영구 clone**으로 유지 (기존 `mktemp` + `trap rm` 임시 clone 대체, `git pull --ff-only`로 갱신)
- `install.sh`: 설치 완료 후 `~/.ai-skills/installs.json`에 `{mode, scope, target_dir}` 기록 (동일 `target_dir` dedupe), `~/.ai-skills/bin/ai-skills` 배치 + `chmod +x`, 셸 rc(`~/.zshrc`/`~/.bashrc`)에 전용 마커(`# AI-SKILLS-PATH:START/END`)로 PATH 1회 등록 (idempotent)

### Changed

- `README.md` 설치 섹션에 `ai-skills update` / `ai-skills version` 사용법 추가, 기존 `curl | bash ... --update`는 "최초 설치 또는 CLI 미등록 환경용"으로 재배치
- `--local` 설치는 영구 clone / 설치 기록 / CLI·PATH 등록을 전부 스킵 (개발·테스트 경로 유지)

## [0.4.9] - 2026-07-07

### Added

- `caveman` 스킬 번들 추가 — [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (MIT License)에서 vendoring
  - `.claude/skills/caveman/SKILL.md`, `README.md`, `LICENSE` 추가 (원 저작권 고지 보존)
  - `README.md`에 `/caveman` 섹션 및 프로젝트 구조 다이어그램 항목 추가

### Changed

- `task-plan`, `implement`, `qa-guide`, `skill-creator`: `## Communication Style` 섹션의 `caveman` 적용을 "설치되어 있으면"에서 필수 적용으로 변경 — 이제 저장소에 번들되어 있으므로 무조건 사용

## [0.4.8] - 2026-07-07

### Changed

- `task-plan`, `implement`, `qa-guide`, `skill-creator`: added a `## Communication Style` section instructing each skill to apply the (optional, personally-installed) `caveman` skill to conversational chatter and free-text prose sections, to cut down on verbose output
  - Scope: chat responses (approach summaries, completion/validation reports, review prompts) AND free-text prose inside generated documents (개요, 엣지 케이스 설명, 진행 기록 등)
  - Explicitly excluded: structured elements — tables, checklists, header fields, code blocks, file paths — stay in normal format regardless of caveman mode
  - Guarded with "if available" at the time — later bundled directly into the repo, see 0.4.9

## [0.4.7] - 2026-07-01

### Removed

- `evaluate` 스킬 제거 (deprecated) — 체크리스트 기반 코드 품질 평가 워크플로우 전체 폐기
- `finalize` 스킬 제거 (deprecated) — 작업 문서 최종 정리(임시 문서 삭제 + Implementation Map 병합) 워크플로우 전체 폐기
- `install.sh`: `cleanup_legacy_skills()`에 `evaluate`, `finalize` 추가 — `--update` 실행 시 기존 설치에서 자동 삭제
- `install.sh`: 버전 `0.4.7`으로 갱신

### Changed

- `implement` 스킬에서 `evaluate`/`finalize` 관련 참조 제거
  - Step 3 완료 처리에서 "`/evaluate` 실행 제안" 항목 삭제
  - `evaluate.md` 기반 위반사항 수정 워크플로우였던 "Step 5: Evaluation-Based Fixes" 섹션 전체 삭제
  - Rules에서 "Evaluation-based fixes are limited to violation items" 항목 삭제
- `skill-creator/references/directory-structure.md`: "Full" 복잡도 예시를 `/evaluate` → `/skill-creator`로 교체 (더 이상 존재하지 않는 스킬을 예시로 두지 않기 위함)
- `README.md`: `/evaluate`, `/finalize` 섹션 및 프로젝트 구조 다이어그램에서 관련 항목 제거
- `install.sh`: Cursor용 `AGENTS.md` 워크플로우 표에서 `evaluate` 행 제거

### Migration

- `--update`로 재설치하면 `.claude/skills/evaluate/`, `.claude/skills/finalize/`가 자동 삭제됩니다.
- 이전에 `/evaluate`로 생성한 `evaluate.md`, `/finalize`가 정리한 산출물은 **사용자 산출물**이므로 자동 삭제되지 않습니다. 필요 시 수동 정리하세요.
- 코드 품질 체크가 필요하면 별도 도구를 사용하거나 직접 리뷰하세요. 작업 문서 정리가 필요하면 수동으로 임시 문서를 삭제하세요.

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

## [0.4.6] - 2026-07-01

### Changed

- `qa-guide` 스킬을 슬림화된 task-plan 산출물에 맞춰 정렬
  - 참조 문서를 `docs/<name>/plans/tasks.md` + `spec.md` 두 개로 축소 — `README.md` / `progress.md` / `findings.md` 참조 전부 제거
  - 자동 감지를 `docs/*/plans/tasks.md` 헤더의 `상태: 진행중 | 완료` grep으로 변경
  - jira-issue 인자 매칭을 `tasks.md` 헤더 `이슈:` 필드 기준으로 변경
  - `test-case`의 "휴먼 테스트" 요소를 가볍게 흡수: "사전 준비"를 "사전 조건" / "테스트 데이터" 두 섹션으로 분리, 2개 이상 상태/옵션 조합이 있는 시나리오는 별도 매트릭스 없이 같은 시나리오 표에 조합별 행을 추가하는 규칙 도입
- `finalize` 스킬에서 `test-cases.md` 관련 참조 제거 (Step 1 문서 읽기, preserve 표, 완료 리포트, Rules)

### Removed

- `test-case` 스킬 제거 (deprecated) — agent-browser/e2e 자동화를 겨냥한 조합 매트릭스, 표준화 액션 동사, 셀렉터 힌트, YAML 자동화 메타데이터 등 무거운 산출물을 폐기하고, 사람이 읽는 유용한 부분만 `qa-guide`로 이관
- `install.sh`: `cleanup_legacy_skills()`에 `test-case` 추가 — `--update` 실행 시 기존 설치에서 자동 삭제
- `install.sh`: 버전 `0.4.6`으로 갱신

### Migration

- `--update`로 재설치하면 `.claude/skills/test-case/`가 자동 삭제되고 `qa-guide/SKILL.md`가 새 버전으로 덮어쓰기 됩니다.
- 이전에 `/test-case`로 생성한 `test-cases.md`는 **사용자 산출물**이므로 자동 삭제되지 않습니다. 필요 시 수동 정리하세요. 앞으로 인간이 읽는 테스트 문서는 `/qa-guide`로 생성합니다.
- agent-browser/e2e 자동화 파싱용 산출물이 필요하다면 이번 변경으로 더 이상 제공되지 않으니, 별도 도구나 직접 작성이 필요합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

## [0.4.5] - 2026-05-20

### Changed

- `implement` 스킬을 슬림화된 task-plan 산출물에 맞춰 정렬
  - 참조 문서를 `tasks.md` + `spec.md` 두 개로 축소 — `README.md` / `findings.md` / `ui-spec.md` / `progress.md` 참조 전부 제거
  - 경로를 `docs/<name>/plans/`로 통일 (자동 감지는 `docs/*/plans/tasks.md` 헤더의 `상태: 진행중` grep)
  - Phase 진행 기록을 별도 `progress.md`가 아닌 `tasks.md`의 `## 진행 기록` 섹션에 누적
  - 전체 완료 처리는 `tasks.md` 헤더 `상태:` 필드를 `완료`로 변경 (별도 `README.md` 상태 갱신 제거)
  - Approach summary 입력 출처를 `findings.md` 대신 `tasks.md` Phase task의 sub-bullet(재사용/패턴) + `spec.md`로 변경
- `rules/react-typescript.md`: 단일 "성능" 섹션을 **렌더링**과 **메모이제이션** 두 섹션으로 분리
  - **렌더링** (React 기본기): 안정적 key, 렌더링 주체 격리, 상태 위치, 파생 값 — 리렌더 이슈는 이 구조적 해결을 먼저 시도
  - **메모이제이션**: `useMemo` / `useCallback` / `React.memo`는 **사용자가 명시적으로 요청할 때만** 도입 — 측정 없이 선제적으로 추가 금지
  - 기존 `컴포넌트 패턴`의 key 규칙과 파생 값 규칙은 `렌더링` 섹션으로 이동
  - `implement` Rules 및 Step 2-2에도 "렌더링 구조 우선, 메모이제이션은 사용자 요청 시에만" 명시
- `install.sh`: 버전 `0.4.5`로 갱신

### Migration

- `--update`로 재설치하면 `implement/SKILL.md`와 `rules/react-typescript.md`가 diff 확인 후 덮어쓰기 됩니다. 이번 변경으로 ai-skills 자체에서 새로 삭제되는 파일은 없습니다 (기존 `cleanup_legacy_skills` / `cleanup_legacy_agents` / `cleanup_task_plan_legacy`로 충분).
- 사용자가 이전 `implement` 버전으로 만든 `docs/<name>/` 하위의 `README.md` / `findings.md` / `ui-spec.md` / `progress.md`는 **사용자 산출물**이므로 설치 스크립트가 자동 삭제하지 않습니다. 필요 시 수동 정리하세요. 새로 시작하는 작업은 `docs/<name>/plans/tasks.md`의 `## 진행 기록`만 사용합니다.
- `react-typescript.md`를 커스터마이즈했다면 `--update` 시 diff가 표시되니 확인 후 덮어쓰기/스킵을 선택하세요.

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

## [0.4.4] - 2026-05-20

### Changed

- `task-plan` 스킬 전면 슬림화 — SKILL.md 570→69줄, 산출물을 `tasks.md` + `spec.md` 2개로 축소
  - 작업 종류(버그 수정 / 기능 개발 / 기능 수정)는 `tasks.md` 헤더 메타데이터로만 표시 — 별도 템플릿 분기 제거
  - 코드베이스 탐색 결과(재사용 컴포넌트, 라이브러리 패턴, 관련 파일)는 Phase 항목의 sub-bullet로 인라인
  - Figma 노드는 task 라인에 인라인 링크로 표기, 한 노드가 여러 sub-area에 매핑되면 task 라인을 분리
  - "기능 수정" 작업은 원본 plans에 `참조:` 헤더 링크만 추가, 원본 파일은 수정하지 않음
  - PR 생성은 `/git-pr`에 위임 (Creating-PR / PRD-change 섹션 제거)

### Removed

- `task-plan/templates/`: `README.template.md`, `findings.template.md`, `progress.template.md`, `ui-spec.template.md` 제거
- `task-plan/references/`: `compliance-checklist.md`, `design-handling.md`, `exploration-strategy.md` 폴더 통째로 제거
- SKILL.md에서 grill-me 인터뷰 / 타입 분기 / compliance check / context monitor / inline fallback / task completion / session handoff 섹션 제거

### Fixed

- `install.sh`: `cleanup_task_plan_legacy()` 추가 — `--update` 실행 시 폐기된 `task-plan/references/`, `task-plan/agents/`, 레거시 템플릿 파일(`README`, `findings`, `progress`, `ui-spec`) 자동 정리

## [0.4.3] - 2026-04-22

### Added

- `git-pr` 스킬 추가 — 브랜치 작업 + PR 생성 통합 인터랙티브 워크플로우
  - 새 브랜치 생성 / 현재 브랜치 사용 두 가지 모드 지원 (`--mode git|pr|both`)
  - 서브 브랜치(-dev/-stg) 생성 및 리베이스 플로우
  - 리베이스 충돌 발생 시 파일별 분석 → 사용자 승인 → 해결 루프 자동 처리
  - PR 초안 자동 생성 — 커밋 로그와 diff stat 분석으로 제목·본문 초안 작성 후 사용자 확인. 구현사항·특이사항·핵심 리뷰 포인트·테스트 케이스 자동 채움, 구현 화면은 사용자가 직접 추가
  - 모든 사용자 안내 메시지 한국어 처리

### Changed

- `git-branch`, `pr` 스킬을 `git-pr`로 통합 및 삭제
- `task-plan` 스킬: opusplan 모델 감지 및 서브에이전트 위임 로직 제거 — Claude Code가 세션 중 모델 전환을 지원하지 않아 실효성이 없고, v0.4.0의 "서브에이전트 없이 직접 실행" 원칙과도 충돌하여 삭제
- `investigate` 스킬 삭제

### Fixed

- install.sh: `cleanup_legacy_skills()` 추가 — `--update` 실행 시 레거시 스킬 디렉토리(`git-branch/`) 자동 정리

## [0.4.2] - 2026-04-08

### Changed

- 모든 스킬 산출물(템플릿 + 인라인 출력 예시)을 한국어로 통일
  - `task-plan`, `study`, `evaluate`, `implement`, `finalize`, `test-case`, `skill-creator` — 언어 규칙을 "산출물은 한국어로 작성"으로 변경
  - `evaluate/templates/report.md`, `project-context-block.md` — 헤더/라벨 한글화
  - `test-case/templates/test-cases.template.md` — 헤더/라벨/주석 한글화
  - `study/SKILL.md` — 케이스 스터디 구조 템플릿 한글화
  - `implement/SKILL.md` — 접근법 요약, progress 기록, QA 안내 메시지 한글화
  - `finalize/SKILL.md` — 구현 맵 테이블, 완료 리포트, 에지 케이스 메시지 한글화
- CLAUDE.md Language Rules 예외에 skill output templates 추가

## [0.4.1] - 2026-04-06

### Added

- `/finalize` 스킬 추가 — 구현, 평가, QA 완료 후 작업 문서를 최종 정리. spec.md에 Implementation Map을 병합하고 임시 문서(findings, tasks, progress, evaluate, qa-report, qa-guide)를 삭제. `/finalize <task-folder-name>`으로 호출.
- spec.md `Implementation Map` 섹션 도입 — spec 항목별로 구현 파일과 기술 결정을 매핑하여, 다른 AI 에이전트(Codex, Gemini, Cursor 등)가 파일 탐색 없이 바로 코드로 진입 가능

## [0.4.0] - 2026-04-06

### Changed

- **아키텍처: 서브에이전트 전면 제거** — 모든 스킬이 서브에이전트 대신 메인 대화에서 직접 실행. 독립 에이전트 컨텍스트 간 중복 파일 읽기가 사라져 토큰 소모 대폭 감소.
- `/implement` — `implement-engineering` / `implement-react` 에이전트 위임 제거, 코드 직접 구현
- `/evaluate` — 5개 병렬 에이전트를 메인 대화의 단일 체크리스트 평가로 대체
- `/task-plan` — `evaluate-docs` 에이전트를 인라인 문서 품질 검사로 대체, 코드베이스 탐색도 Explore 서브에이전트 대신 직접 수행
- `/qa` — 버그 수정을 implement 에이전트 위임 대신 직접 실행
- CLAUDE.md — "전문 에이전트 사용" 규칙을 "직접 구현 (서브에이전트 없음)"으로 교체
- AGENTS.md (Cursor) — 직접 구현 워크플로우에 맞게 전면 재작성
- evaluate 리포트 템플릿 간소화 (에이전트별 섹션 제거)
- install.sh 버전을 v0.4.0으로 업데이트

### Removed

- 에이전트 파일 8개 삭제: `implement-engineering.md`, `implement-react.md`, `evaluate-react.md`, `evaluate-engineering.md`, `evaluate-a11y.md`, `evaluate-security.md`, `evaluate-performance.md`, `evaluate-docs.md`
- 삭제된 에이전트의 메모리 디렉토리 제거
- install.sh에서 `--only agents` 옵션 제거
- install.sh에서 "skills가 agents에 의존" 로직 제거

### Added

- install.sh: `cleanup_legacy_agents()` 추가 — `--update` 실행 시 레거시 에이전트 파일과 빈 `agents/` 디렉토리 자동 정리
- README.md: v0.3.1 → v0.4.0 마이그레이션 가이드 추가

## [0.3.1] - 2026-04-06

### Added

- `.claude/docs/` 폴더 추가 — 프로젝트별 UI 패턴 레퍼런스 문서 저장 위치
- `docs/partner-jirisan.md` — white_label admin/partner 앱용 Jirisan DataTable 패턴 레퍼런스
- `docs/partner-option-group-factory.md` — white_label admin/partner 앱용 OptionGroupFactory (Advanced Search) 패턴 레퍼런스
- install.sh: `docs/` 폴더 설치 지원 및 `--only docs` 옵션 추가

### Changed

- task-plan: white_label + admin/partner 작업 시 Figma에서 table/search-filter UI 감지 → 해당 패턴 문서 참조 후 ui-spec.md에 `## Pattern Reference` 섹션으로 embed
- CLAUDE.md: 레포 내 모든 기록은 영어로 작성하는 언어 규칙 추가

## [0.3.0] - 2026-04-01

### Changed

- 평가/구현 에이전트 출력 템플릿을 영어로 전환 — "Write results in Korean" → "Write results in the user's language"
- investigate 스킬 삭제 → task-plan 스킬에 bug 타입 분기로 통합 (증상 수집 → 가설 생성 → 검증 루프)
- useEffect 의존성 배열 규칙을 exhaustive-deps에서 무한루프 방지 중심으로 변경
- evaluate-react의 Hook 규칙에서 eslint-disable 관련 항목 제거, 무한루프 판단 기준 추가

### Added

- evaluate, qa, test-case 스킬에 task-plan progress.md 연동 섹션 추가
- qa 스킬 browse 바이너리 탐색에 `.cursor/` 경로 지원

### Removed

- `/investigate` 스킬 및 템플릿 파일 5개 (SKILL.md, findings.md, hypothesis.md, save-policy.md, symptom-block.md)
- install.sh AGENTS.md에서 investigate 스킬 참조 제거

## [0.2.1] - 2026-04-01

### Added

- browse 바이너리 탐색에 `.cursor/` 경로 지원 (프로젝트 로컬 + 글로벌)

### Changed

- browse 내부 상태 디렉토리를 `.gstack/`에서 `.ai-skills/`로 마이그레이션 (chromium-profile, sidebar 등)

## [0.2.0] - 2026-04-01

### Added

- /browse 스킬 추가 — 헤드리스 브라우저로 웹 앱 탐색/테스트/스크린샷
- /qa 스킬 추가 — task-plan 문서 기반 브라우저 QA 검증
- install.sh에 browse 셋업 안내 (Playwright Chromium)
- /implement 완료 후 /qa 검증 안내 메시지 추가

## [0.1.1] - 2026-04-01

### Added

- 평가 에이전트 3종 추가: evaluate-a11y (접근성), evaluate-security (보안), evaluate-performance (성능)
- /evaluate가 5개 에이전트 병렬 실행으로 확장 (기존 2개 → 5개)
- /investigate 스킬 추가 — 체계적 디버깅 + 근본원인 분석

### Changed

- evaluate 에이전트를 skills 내장에서 프로젝트 agents 디렉토리로 이동
- evaluate-docs 에이전트 경로를 프로젝트 agents 디렉토리로 변경
- 평가 리포트 템플릿에 접근성/보안/성능 섹션 추가
- install.sh: --only skills 시 agents도 함께 설치 (의존성)
- install.sh: Cursor용 AGENTS.md에 investigate 스킬 및 신규 에이전트 반영

## [0.1.0] - 2026-04-01

### Added

- 초기 skills 구성 (evaluate, task-plan)
- 에이전트 추가 (evaluate-react, evaluate-engineering, evaluate-docs)
- `install.sh` 배포 스크립트 추가
- `install.sh`에 `--claude`/`--cursor`, `--global`/`--project` 옵션 지원
- skill-creator 스킬 추가

### Changed

- evaluate skill을 모듈화 구조로 리팩토링
- task-plan skill을 모듈화 구조로 리팩토링
- README 전면 개선 및 CURSOR_SETUP_GUIDE 제거

### Fixed

- CLAUDE.md 문서 수정
- install.sh 버그 수정
- 업데이트 시 커스텀 내용 덮어쓰기 경고 추가
