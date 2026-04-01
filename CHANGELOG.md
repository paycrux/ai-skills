# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
