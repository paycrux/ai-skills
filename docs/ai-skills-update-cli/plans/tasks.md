# ai-skills 업데이트 CLI (`ai-skills update`)

> 이슈: 없음
> 작업 종류: 기능 개발
> 상태: 완료
> 생성일: 2026-07-07

## 개요

`docs/skill-composition-and-update-proposal.md`(김하진 건의)에서 출발한 업데이트 드리프트 문제를 다시 논의한 결과, 에이전트(Claude Code/Cursor/Codex) 훅에 의존하는 자동 업데이트는 기각했다. 각 에이전트가 훅 스키마를 따로 구현해야 하고, 그중 Cursor의 `sessionStart` 훅은 2026년 초 기준 `additional_context` 주입 버그가 있어 신뢰할 수 없다. 대신 실제 마찰의 근원 — 매번 `curl | bash` 전체를 다시 받아야 하는 설치 구조 — 를 없앤다.

`install.sh`가 임시 디렉터리에 clone 후 버리는 대신 `~/.ai-skills/repo`에 영구 clone을 유지하고, 짧은 전역 커맨드 `ai-skills update` 하나로 pull + 재설치를 수행하게 한다. 에이전트나 훅과 무관한 순수 셸 도구이므로 Claude Code/Cursor/Codex 어느 쪽을 쓰든 동일하게 동작한다. 범위: 영구 clone, 설치 기록, `ai-skills` CLI, PATH 등록. 제외: 셸 시작 시점 자동 감지/자동 실행(자동 pull은 하지 않음 — 실행은 항상 사용자가 `ai-skills update`를 직접 호출).

## Phase 1: 영구 clone + 설치 기록

- [x] `install.sh`에 영구 소스 디렉터리 로직 추가 (`~/.ai-skills/repo`) (`install.sh`)
  - 재사용: 기존 `--local` 분기의 `SRC_DIR` 설정 패턴 — `--local`일 때는 이 로직을 완전히 건너뛰고 기존처럼 로컬 `.claude/`를 그대로 사용
  - `~/.ai-skills/repo`가 없으면 `git clone`, 있으면 `git pull --ff-only` (충돌/실패 시 명확한 에러 메시지 + 수동 삭제 안내)
  - 임시 디렉터리(`mktemp -d` + `trap rm`) clone 경로는 유지하되 `--local`이 아닐 때의 기본 동작을 영구 clone으로 전환
- [x] 설치 완료 후 설치 기록 저장 (`install.sh`)
  - `~/.ai-skills/installs.json`에 `{mode, scope, target_dir}` append, 동일 `target_dir` 있으면 갱신(dedupe)
  - `--local` 설치는 기록하지 않음 (개발/테스트용이므로 업데이트 대상에서 제외)

## Phase 2: `ai-skills` 전역 CLI

- [x] CLI 스크립트 작성 (`bin/ai-skills`)
  - `update` 서브커맨드: `~/.ai-skills/repo`에서 `git pull` → `installs.json`에 기록된 모든 대상에 대해 `install.sh --update`를 저장된 mode/scope로 재실행
  - `version` 서브커맨드: 로컬 설치 버전과 원격 최신 버전(`git -C ~/.ai-skills/repo log`/remote HEAD 기준)을 비교해 출력
  - 기록된 설치 대상이 없으면 "먼저 install.sh로 설치하세요" 안내 후 종료
- [x] `install.sh`가 `bin/ai-skills`를 `~/.ai-skills/bin/ai-skills`로 복사 + `chmod +x` (`install.sh`)
- [x] PATH 등록 (`install.sh`)
  - 재사용: `merge_claude_md`의 `MARKER_START`/`MARKER_END` 마커 삽입·치환 로직을 그대로 응용해 셸 rc 파일에 적용
  - `$SHELL` 감지해 `~/.zshrc`(zsh) 또는 `~/.bashrc`(bash)에 `export PATH="$HOME/.ai-skills/bin:$PATH"`를 마커로 감싸 1회만 삽입 (이미 있으면 스킵)
  - zsh/bash가 아니면 자동 등록을 건너뛰고 수동 등록 안내 문구 출력
  - 설치 완료 메시지에 "새 터미널을 열거나 `source ~/.zshrc`를 실행해야 `ai-skills` 커맨드를 쓸 수 있다"는 안내 추가

## Phase 3: 문서화

- [x] `README.md` 설치 섹션에 `ai-skills update` 사용법 추가 (`README.md`)
  - 기존 `curl | bash ... --update` 예시는 "최초 설치 또는 CLI 미등록 환경용" 안내로 유지
- [x] `CHANGELOG.md`에 버전 항목 추가 (`CHANGELOG.md`)
- [x] `install.sh`의 `VERSION` 값 bump (`install.sh`)

## 진행 기록

### 2026-07-07

- 작업 내역: 계획 최초 작성. 에이전트 훅 기반 자동 업데이트(Claude SessionStart, Cursor sessionStart, Codex hooks.json) 검토 후 기각 — 에이전트별 재구현 필요 + Cursor 훅 버그로 신뢰 불가. 순수 셸 기반 영구 clone + `ai-skills update` CLI로 방향 확정.
- Phase 1: 영구 clone + 설치 기록 완료 — `install.sh` 수정. 비-`--local` 소스 해석을 임시 clone → 영구 clone(`~/.ai-skills/repo`, `git clone`/`pull --ff-only`, `--depth 1` 제거)로 전환. `record_install()`(python3) 추가로 `~/.ai-skills/installs.json`에 `{mode,scope,target_dir}` 기록 + `target_dir` dedupe, `--local` 스킵. `bash -n` 통과.
- Phase 2: `ai-skills` 전역 CLI 완료 — `bin/ai-skills` 신규 작성(`update`/`version`/`help`). `update`는 clone pull 후 `installs.json` 순회, project scope는 `target_dir` 상위로 `cd` 후 `install.sh --update` 재실행. `version`은 로컬 clone vs `origin/HEAD` VERSION 비교. `install.sh`에 `install_cli()`(clone 루트 `bin/ai-skills` → `~/.ai-skills/bin`, chmod +x) + `register_path()`(전용 마커 `# AI-SKILLS-PATH:START/END`, `$SHELL` 감지, idempotent) 추가. 완료 메시지에 reload/`which ai-skills` 안내 추가. 검증: JSON dedupe·TSV·version 파싱, install_cli 복사·chmod, register_path 멱등성(마커 1개) 하네스 테스트 통과. (전체 대화형 e2e는 샌드박스에 tty 없어 미실행 — 사용자 로컬 검증 권장)
- Phase 3: 문서화 완료 — `README.md`에 "업데이트 (`ai-skills` CLI)" 섹션 추가(`ai-skills update`/`version` 주 경로, 기존 `curl | bash --update`는 미등록 환경용으로 재배치, reload/PATH 안내 포함). `CHANGELOG.md` `[0.5.0]` 항목 추가. `install.sh` `VERSION` 0.4.9 → 0.5.0 bump. `bash -n` 통과.
- 전체 완료 — 3개 Phase 모두 구현·검증. 변경 파일: `install.sh`, `bin/ai-skills`(신규), `README.md`, `CHANGELOG.md`.
