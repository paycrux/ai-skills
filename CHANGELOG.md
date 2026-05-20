# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
