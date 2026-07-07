# ai-skills 업데이트 CLI (`ai-skills update`) - 명세

## 화면/기능 흐름

- 최초 설치(`curl | bash install.sh`): 기존 파일 복사 완료 → `~/.ai-skills/repo` 영구 clone 생성 → `installs.json`에 설치 기록 → `~/.ai-skills/bin/ai-skills` 배치 → 셸 rc에 PATH 마커 삽입(최초 1회) → "새 터미널을 열거나 source 하라"는 안내 출력
- 재설치(같은 대상에 다시 `install.sh` 실행): 영구 clone은 `git pull --ff-only`로 갱신, `installs.json`은 동일 `target_dir` 항목을 갱신(중복 추가 없음)
- 업데이트(`ai-skills update`): 영구 clone pull → `installs.json`에 기록된 모든 대상을 순회하며 각 mode/scope로 `install.sh --update` 재실행 → 기존과 동일한 diff 확인/덮어쓰기 프롬프트 그대로 노출
- 버전 확인(`ai-skills version`): 로컬 설치 버전과 원격 최신 버전을 나란히 출력, 최신이면 "이미 최신"으로 표시
- PATH 미반영 상태에서 `ai-skills` 실행: 셸이 아직 rc를 다시 읽지 않아 `command not found` → 이 경우는 CLI가 아니라 셸 자체의 동작이므로 설치 완료 메시지에서 미리 안내
- `--local` 플래그로 설치: 영구 clone/설치 기록/PATH 등록 전부 스킵, 기존처럼 로컬 `.claude/`만 사용 (개발 테스트용 경로는 건드리지 않음)

## 상태 정의

| 상태                          | 설명                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| 설치 기록 없음 (최초)         | `~/.ai-skills/installs.json` 자체가 없음 → `ai-skills update`가 "먼저 install.sh로 설치하세요" 안내 후 종료 |
| 설치 기록 있음, clone 정상    | `git pull --ff-only` 성공 → 기록된 대상에 `--update` 순회 실행        |
| 설치 기록 있음, clone 손상    | `~/.ai-skills/repo`가 dirty/rebase 중/history diverge 등으로 `--ff-only` 실패 → 에러 메시지 + `rm -rf ~/.ai-skills/repo` 후 재설치 안내 |
| 로컬 커스터마이징 있음        | 대상 파일이 배포본과 다름 → 기존 `copy_dir`의 diff 프롬프트(overwrite/skip/전체 diff) 그대로 노출 |
| 지원 안 되는 셸(fish 등)      | PATH 자동 등록 생략, 수동 등록 문구만 출력                            |

## 엣지 케이스

- 여러 프로젝트에 각각 `--project`로 설치한 경우: `installs.json`에 여러 `target_dir`이 누적되고, `ai-skills update`는 전부 순회하며 각각 결과를 요약 출력
- `~/.ai-skills/bin`에 이미 동명의 다른 실행 파일이 PATH 우선순위상 앞서 존재: 설치 완료 메시지에서 `which ai-skills`로 확인하라는 경고 추가
- 셸 rc에 마커(`AI-SKILLS-PATH:START/END` 등 `merge_claude_md`와 별개의 전용 마커)가 이미 있는 경우: 재삽입하지 않고 스킵 (idempotent)
- 네트워크 오프라인 상태에서 `ai-skills update` 실행: `git pull` 실패를 그대로 노출하고 "오프라인이거나 원격에 접근할 수 없습니다" 안내로 종료(세션/설치를 막지 않음)
- 원격 저장소 자체가 삭제/이동된 경우: `git pull`의 원본 에러 메시지를 그대로 보여주고 수동 재설치 안내
