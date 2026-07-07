# ai-skills CLI 개선 — update 선택 프롬프트 항상 노출 + install 명령 추가

> 이슈: 없음
> 작업 종류: 기능 수정
> 상태: 완료
> 생성일: 2026-07-07

## 개요

핵심: `ai-skills update`도 `ai-skills install`(신설)도 **옵션 없이 그냥 치면 항상 대화형 프롬프트**로 뜬다. `--claude` 같은 플래그는 스크립트/CI용 지름길일 뿐 필수 아님.

`ai-skills update` 지금 대상 1개면 프롬프트 없이 바로 진행함. 근데 유저 원하는 건 "매번 claude/cursor/codex 중 뭐 업데이트할지 확인" — 대상 개수 상관없이 그냥 치면 항상 물어봐야 함. 대상 1개일 때 스킵하는 분기(`bin/ai-skills:123-125`) 지워서 항상 피커 뜨게 고침. 플래그는 프롬프트 건너뛰고 싶을 때만 쓰는 옵션으로 그대로 유지.

추가로 `ai-skills install` 신설 — 아직 안 깐 에이전트(cursor, codex 등) 새로 추가할 때 쓰는 명령. 그냥 `ai-skills install`만 치면 `~/.ai-skills/repo` pull 후 `install.sh`가 자체적으로 갖고 있는 "어떤 에디터? → 어떤 범위?" 대화형 프롬프트로 바로 들어감(이미 있는 로직 재사용, 중복 구현 안 함) — 플래그 없이도 완전히 대화형. `--claude --global` 같은 플래그는 스크립트에서 프롬프트 생략하고 싶을 때만 쓰는 선택 사항. 범위: `bin/ai-skills` 수정, README/CHANGELOG 반영. 제외: install.sh의 에디터/범위 선택 로직 자체 변경 없음.

## Phase 1: `ai-skills update` 항상 선택 프롬프트

- [x] 대상 1개일 때 자동 스킵하던 분기 제거, 항상 인터랙티브 피커로 진입하게 정리 (`bin/ai-skills`)
  - 재사용: 기존 피커 출력/파싱 로직 (`bin/ai-skills:127-151`) 그대로, 분기만 제거
  - `--claude`/`--cursor`/`--codex`/`--all` 플래그 준 경우, non-tty인 경우는 그대로 프롬프트 스킵 유지
- [x] `cmd_help`의 update 안내 문구에서 "대상이 둘 이상일 때"라는 조건 제거 (`bin/ai-skills`)

## Phase 2: `ai-skills install` 명령 추가

- [x] `cmd_install()` 함수 작성 — 저장소 pull 후 인자 그대로 `install.sh`에 위임 (`bin/ai-skills`)
  - 재사용: `cmd_update()`의 `git pull --ff-only` 에러 처리 블록 (`bin/ai-skills:60-64`) 그대로
  - 플래그 없이 `ai-skills install`만 쳐도 `install.sh` 자체 대화형 프롬프트(에디터 선택 → 범위 선택, `install.sh:128-154`)로 바로 들어감 — 기본 경로가 대화형, 별도 구현 안 함
  - project scope는 현재 작업 디렉터리 기준으로 설치되므로(`install.sh`의 `$(pwd)` 사용), cd 처리 불필요
- [x] dispatch에 `install` 라우팅 추가 (`bin/ai-skills`)
- [x] `cmd_help`에 `install` 명령 + 옵션(`--claude`/`--cursor`/`--codex`/`--global`/`--project`/`--only`) 설명 추가 (`bin/ai-skills`)

## Phase 3: 문서/버전 반영

- [x] README.md에 `ai-skills install` 사용법 추가, update 섹션의 "둘 이상일 때"도 같이 수정 (`README.md`)
- [x] CHANGELOG.md에 0.5.2 항목 추가, `install.sh`의 `VERSION` 갱신 (`CHANGELOG.md`, `install.sh`)

## 진행 기록

### 2026-07-07

- 문서 생성
- 유저 확인: 플래그 없이도 이미 대화형 프롬프트로 뜨는 게 맞음 — 문구가 "플래그로 지정해야 하는 것"처럼 읽혀서 헷갈렸다고 함. 개요/Phase 2 문구를 "플래그 없이 그냥 치면 항상 대화형"으로 명확히 수정
- Phase 1 완료 — `bin/ai-skills`의 대상 1개 스킵 분기 제거, `cmd_help` 문구 수정. expect로 대상 1개 상태에서도 프롬프트 뜨는 것 검증함
- Phase 2 완료 — `cmd_install()` 신설, dispatch/`cmd_help`에 반영. expect로 무인자 대화형 진입 + `--cursor --global` 플래그 위임 둘 다 검증함
- Phase 3 완료 — README에 `install` 사용법 섹션 추가, update 문구 수정. CHANGELOG 0.5.2 항목 추가, `install.sh` VERSION 0.5.2로 올림
- 전체 완료. 프론트엔드 작업 아니라 QA 브라우저 검증 대상 아님
