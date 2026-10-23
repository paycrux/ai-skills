# flow 스킬 — 작업 인계 (2026-10-23)

> 다음 세션은 이 문서부터 읽고 시작한다. 브랜치 `feat/flow-skill`, 저장소 `~/projects/ai-skills`.

## 1. 목표

ai-skills 1.0.0 메이저 업데이트. 두 가지를 하나로 묶는다.

- **사람이 읽는 문서**: 작업 하나가 `docs/<작업명>/` 안의 HTML 페이지 묶음이 되고, 브라우저로 웹페이지처럼 넘겨 본다. 문서를 용도별로 쪼개 늘리지 않고, 단계 흐름 하나로 본다.
- **SOT 맵 방법론**: 화면 요소마다 값이 어디서 오는지(서버 필드 그대로 / 앱 가공 / 동작 / 미정 / 범위 제외)를 Figma 위 번호와 표로 짝짓고, 화면 밖 상태까지 적는다. 프론트 개발 중 데이터 흐름과 UI 상태를 이 표로 확인한다.

출처

- 팀 논의 슬랙 스레드: https://example.slack.com/archives/C00000000/p0000000000000000
  - 결론: 사람과 AI가 읽는 문서를 나누지 않는다 / 문서는 쪼개지 말고 압축 / `index.html`을 지도로 / 도메인 문서는 사이클이 한 번 끝난 뒤
- SOT 맵 원본: example-app 저장소 `main` 브랜치 `.claude/skills/sot-map/`(팀원 A 작성). `SKILL.md`, `build.py`, `template.html`

## 2. 결정된 것

그릴링 1·2라운드와 이후 대화에서 정한 것. 바꾸려면 사용자와 다시 합의한다.

> **2026-10-23 구조 변경으로 아래 표의 일부가 바뀌었다 — 자세한 내용은 [`redesign.md`](redesign.md).**
> 바뀐 행: 문서 구조(작업 폴더 → 도메인 폴더 + `screens.json` · `tasks/<작업 ID>.json`), 결론 블록 · index 동기화(HTML 결론 블록 → json의 `conclusion`, 뷰어가 그림), 저장 방식(폴더 연결 · inbox · apply → `npm run flow` 서버가 json에 직접 저장, 해시로 충돌 확인), 페이지 열기(파일 → 서버 주소), 참조(글자 → `[[S5]]` 같은 ID 링크).
> 그대로인 행: 단계 흐름, spec 없음, 버그 위치, 작은 작업, Figma 스캔 시점, 도메인 문서 제외, 기존 스킬 연결 안 함, 버전, 디자인.

| 항목 | 결정 |
| --- | --- |
| 출발점 | 설치본(`~/.claude/skills`)에서만 고쳐져 있던 HTML 계획 형식을 저장소로 가져와 기준선 커밋(완료) |
| 새 스킬 | `task-plan`은 레거시로 그대로 두고 새 스킬을 만든다. 이름은 임시로 `flow`, 나중에 정함 |
| 문서 구조 | `docs/<작업명>/` — `index.html` + 단계 페이지 6개 + `data/` + `assets/`. 폴더 이름은 작업명, 지라 키는 `data/task.json` |
| 단계 | 01 기획 → 02 화면 · SOT 맵 → 03 질문 → 04 구현 계획 · 구현 → 05 검증 → 06 완료 |
| spec 문서 | 없앤다. 화면 동작은 02 SOT 맵, 결정은 03 |
| 결론 블록 | 모든 단계 페이지 맨 위. 다음 단계는 앞 단계의 결론만 읽는다(토큰 절약). 결론과 결정은 사람이 읽는 문장으로 — 키워드를 점으로 잇지 않는다 |
| index 동기화 | 왼쪽 단계 목록과 개요는 `build.py`가 각 페이지의 결론 블록에서 만든다. 손으로 맞추지 않는다 |
| 질문 | 03 페이지가 곧 답하는 화면. 결정된 뒤에도 고칠 수 있고, 고친 답은 Claude가 반영할 때까지 "반영 전"으로 표시. 질문은 SOT 맵의 미정 행, 구현 중 막힘, 검증 중 판단 필요에서 생긴다 |
| 버그 | 리포트는 05 검증에 쌓고 지우지 않는다. 고치는 일은 04에 `B1 수정` 항목 |
| spec을 구현 후에도 고치나 | 고친다. 06 완료에서 SOT 맵 근거를 실제 코드 파일:줄로 바꾼다 |
| sot-map | ai-skills를 원본으로 삼고 가져온다(방법론은 `flow`에 녹였고, 단독 스킬 가져오기와 원작자 합의는 남음) |
| SOT 맵 위치 | 작업 폴더 안 파일. Artifact 게시는 하지 않는다(Artifact 없는 환경이 있음) |
| 서버 저장소 경로 | 사람마다 달라서 `.git/flow.env`의 `SERVER_REPO=`에 한 번 묻고 저장 |
| 저장 방식 | 서버 없이. 크롬 계열 브라우저에서 페이지의 폴더 연결(File System Access API)로 `data/inbox.json`에 쓰고, 사용자가 "저장했어"라고 하면 `build.py apply`가 문서에 반영. 다른 브라우저는 읽기 전용 + 채팅 답 |
| 페이지 열기 | Claude가 사람이 봐야 하는 순간(첫 빌드, 질문, 계획 승인, 완료)에만 `open -a "<크롬 계열>"`로 연다 |
| 작은 작업 | 필요한 단계만 만든다. 파일 하나·결정 하나면 `flow` 없이. 서버 값과 무관한 수정은 04 하나로 시작. 서버 값을 그리는 화면은 01·02·04로 시작. 나머지는 필요해지는 순간 `add` |
| Figma 스캔 시점 | 전역 규칙의 예외로 02 단계만 계획 때 스크린샷과 구조 정보를 받는다. 간격·색 토큰은 여전히 구현 때 |
| 도메인 문서 | 이번 범위에서 뺀다 |
| 기존 스킬 연결 | 이번에는 하지 않는다(`implement`, `qa`, `tracker`, `git-pr`) |
| 버전 | 1.0.0 |

### 디자인 (확정)

- 레이아웃 · 그리드 · 타이포 · 본문 배치는 바젤 스타일: 12단 그리드, 섹션 제목 왼쪽 3단 · 본문 오른쪽 9단, Pretendard, 본문 16px / 줄 간격 1.75
- 바탕과 글자는 흑백, 라이트/다크는 시스템 설정만 따름(전환 버튼 없음)
- 선은 최소: 결론 블록 위 한 줄, 표 머리글 아래 한 줄. 나머지는 여백과 푸른 회색 면(`#f5f7fa`, `#edf1f6`)
- 색은 번호에만: 단계 번호 · 결론 점은 초록 완료 `#1f9d55` · 파랑 진행 중 `#2563eb` · 주황 질문·결정 대기 `#f08c00` · 회색 테두리 시작 전 · 점선 건너뜀. SOT 마커는 빨강 `#e5484d`, 확인 필요 주황, 범위 제외 회색
- 마커 · 배지 · 단계 번호는 둥글게
- 시각 변경은 한 번에 하나씩 하고 스크린샷으로 보여 준다(여러 곳을 한꺼번에 바꾸다 어색해진 적이 있음)

## 3. 현재 상태 (2026-10-23 구조 변경 후)

커밋 `b96d31c` · `49efcd7` · `2e9457d` 위에 구조 변경이 **커밋되지 않은 채** 작업 트리에 있다. 남은 일은 CHANGELOG 1.0.0 갱신과 커밋뿐(사용자가 이번 범위에서 뺌).

| 파일 | 내용 |
| --- | --- |
| `runtime/server.mjs` | 의존성 없는 Node 서버. 트리 · 도메인 데이터 · 저장(해시 비교) · 파일 제공 · 같은 워크트리 서버 재사용 |
| `runtime/viewer/` | `index.html` · `app.js` · `model.js`(상태 계산, 서버와 공유) · `style.css` |
| `scripts/flow.py` | `install` · `find` · `domain` · `task` · `add` · `brief` · `changes` · `clear` · `check` · `merge-xml` |
| `SKILL.md`, `references/*.md` | 새 구조로 다시 씀 |
| 삭제 | `scripts/build.py`, `assets/`, `templates/`, 옛 예시 `docs/flow-skill/examples/` — 사본은 `/tmp/flow-old/`, 삭제 전 미커밋 변경은 `/tmp/flow-uncommitted-before-redesign.diff` (재부팅하면 사라질 수 있음) |
| `README.md`, `install.sh` | `/flow` 설명 갱신 |

## 4. 스킬 구조

```
.claude/skills/flow/
├ SKILL.md
├ references/  documents.md (레이아웃 · JSON · 참조 · 뷰어 · 저장)  sot-map.md  questions.md
├ runtime/     server.mjs  viewer/ (install이 <docs>/.flow로 복사)
└ scripts/flow.py   표준 라이브러리만, Python 3.9+
```

## 5. 확인한 것 / 못 한 것

확인함 (예시 `docs/flow-skill/example-docs/`, 헤드리스 브라우저)

- 작업 한 페이지(01~06), 도메인 SOT 맵(핀 · 표 · "쓰는 곳"), 레거시 md 보기, 찾기
- 참조 미리보기 → 눌러서 도메인 페이지로 이동 · 강조 → 뒤로 가기 시 스크롤 복원, 도메인 간 참조(`[[gift/S8]]`)
- 체크 저장 → JSON에 `"by": "user"`, 충돌(그 사이 파일 변경) 시 저장 거부 + 브라우저에 초안 보관 + 새로고침 후 안내
- 질문 답 저장 → `changes`가 할 일로 출력
- 빈 git 프로젝트에서 `install`(package.json에 스크립트 추가) → `domain` → `task` → `check` → `npm run flow`(포트 겹치면 다음 포트)
- 서버 리소스: 메모리 약 53MB, 대기 중 CPU 0

못 함

1. 결론 · 본문 두 번 눌러 고치기 — 코드만 있고 브라우저로 시험 안 함
2. 다크 모드 화면
3. 실제 티켓으로 `/flow`를 처음부터 끝까지(지시문 검증 안 됨)
4. Cursor · Codex에서 실행

## 6. 남은 일 (권장 순서)

1. CHANGELOG 1.0.0 갱신 + 커밋 (사용자가 따로 지시)
2. "계정 설정" 예시로 01~03을 실제 자료로 채워 보기(아래 7절)
3. 사용자가 앱 저장소에서 `/flow <figma> <notion>`을 처음부터 돌려 봄
4. 전역 규칙 `~/AGENTS.md`와 `install.sh` 안내문의 "/task-plan으로 계획을 세울까요?"를 `/flow` 기준으로, "Merge Into an In-Flight Plan"의 새 폴더 + `참조:` 패턴을 flow의 도메인 규칙과 맞추기
5. sot-map 단독 스킬을 ai-skills로 가져오기 + 팀원 A와 원본 합의
6. `tracker` · `git-pr`와 연결
7. 스킬 이름 정하기

## 7. 실제 자료로 본 예시 — 계정 설정

- Figma 섹션: https://www.figma.com/design/EXAMPLEFILEKEY/example-app?node-id=1-2
- 노션 기획서(더보기 전체, 54,000자): https://www.notion.so/example/00000000000000000000000000000000 — 해당 절은 `2-1. 계정 설정`

섹션 안 프레임 9개 분류(규칙은 `references/sot-map.md`)

| 프레임 | 종류 |
| --- | --- |
| 계정관리 `2465:17303` | 화면 |
| 닉네임 변경 `3609:51498` | 상태(바텀시트) |
| 로그아웃 `3609:51666` | 상태(모달) |
| 개인정보 변경하기(본인인증) `2917:28690`, 변경 실패 `3609:51615`, 본인 인증 실패 `3609:51632` | 외부 화면(본인인증 업체 캡처) + 모달 |
| "ㅤ" `2898:26818` | 주석 — 스낵바, 닉네임 오류 문구, SNS 미연동 · 이메일 없음 · 연동 반려 |
| Group `2917:28827` | 제목 띠 |

미리 보이는 질문: SNS 연동 관리 기획 본문이 "참고"뿐 / 회원탈퇴는 기획 2-1에 있으나 Figma 섹션에 없음 / 로그아웃 프레임의 규칙은 기획 `2-2. 설정` / 기능 네 개라 `/tracker` 분리 여부.

이전 예시: 선물내역 받은 선물 Figma `2507:17556`(마커 계산 시험에 사용).

## 8. 환경

| 항목 | 위치 · 상태 |
| --- | --- |
| 전역 사용 | `~/.claude/skills/flow` → 이 브랜치 폴더로 심볼릭 링크(`~/.claude/skills`는 dotfiles 폴더). 새 세션부터 다른 프로젝트에서 `/flow` 사용 가능 |
| 전역 규칙 | `~/AGENTS.md`(dotfiles)에 "Figma는 구현 때만 스캔"의 `/flow` 02 예외 한 줄 추가 — dotfiles 쪽 미커밋 |
| 메모리 | `~/.claude/projects/-Users-hyunsuko-projects-ai-skills/memory/html-doc-design.md` — 디자인 기준 |
| 예시 | `docs/flow-skill/example-docs/` — 도메인 `gift`(GIFT-101 6단계 전체, R1-Q2 · R2 답이 `"by": "user"`인 시험 상태 / GIFT-102 작은 작업), `coupon`(COUP-7, 다른 도메인 참조), 레거시 샘플 2개. 스킬을 고친 뒤 `flow.py install docs/flow-skill/example-docs`로 뷰어를 다시 복사 |
| 시제품 보드 | Orca 대화 임시 폴더 `grill-board/` — 그릴링 1·2라운드 질문과 답(`data/rounds`, `data/answers`), 워크플로 편집기, iframe 시절 시제품. 서버(4317)는 꺼져 있음 |
| 크롬 확인 | `node docs/flow-skill/example-docs/.flow/server.mjs` → `open -a "Google Chrome" http://127.0.0.1:4317/` |
