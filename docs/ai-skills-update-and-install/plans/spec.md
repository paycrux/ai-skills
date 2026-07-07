# ai-skills CLI 개선 — update 선택 프롬프트 항상 노출 + install 명령 추가 - 명세

## 화면/기능 흐름

- `ai-skills update` (플래그 없음, 기록된 대상 1개): 실행 → 대상 1개짜리 목록 + `a) 전체` 프롬프트 노출 → 사용자가 번호나 `a` 입력 → 해당 대상만 업데이트
- `ai-skills update` (플래그 없음, 기록된 대상 N개, N≥2): 기존과 동일하게 번호 다중 선택 프롬프트
- `ai-skills update --claude` (또는 `--cursor`/`--codex`/`--all`): 프롬프트 안 뜨고 바로 필터링해서 업데이트 (기존 동작 그대로)
- `ai-skills update` (non-tty, 예: CI/파이프): 프롬프트 못 띄우니 기존처럼 전체 업데이트로 폴백
- `ai-skills install` (플래그 없음): 저장소 pull → `install.sh` 위임 실행 → `install.sh` 자체의 "어떤 에디터?"/"설치 범위?" 대화형 프롬프트로 신규 대상 설치
- `ai-skills install --cursor --global`: 프롬프트 없이 바로 cursor/global 설치 진행

## 상태 정의

| 상태             | 설명                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| 대상 0개         | `installs.json` 없음/비어있음 → `update`는 에러, `install`은 항상 가능 |
| 대상 1개         | `update` 실행 시에도 프롬프트 노출 (이번 수정 핵심)                    |
| 대상 N개 (N≥2)   | 기존과 동일하게 번호 선택 프롬프트                                     |
| non-tty 환경     | `update`는 `--all` 취급(자동 전체), `install`은 mode/scope 미지정 시 `install.sh` 자체 에러 처리 |

## 엣지 케이스

- 이미 설치된 mode/scope로 `ai-skills install` 재실행: `install.sh` 자체의 "기존 설치 감지 → Update/Fresh install" 프롬프트가 그대로 뜸, 중복 로직 안 만듦
- `ai-skills install` 실행 중 git pull 실패(오프라인): `ai-skills update`와 동일한 에러 메시지 재사용
- `ai-skills update`에서 대상 1개 상태로 `a` 입력: 기존 "전체 선택" 분기 그대로 재사용, 정상 동작
- `ai-skills install`에 `--only skills` 같은 `install.sh` 기존 플래그를 그대로 전달해도 위임 방식이라 별도 처리 없이 동작
