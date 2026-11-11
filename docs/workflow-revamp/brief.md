# 워크플로 개편 — 스킬 수정 지시서

> 출처: work-flow 세션의 그릴링 R1~R7 (보드 https://claude.ai/artifact/QJ5u7HqY4qNPSTrjuduGnx)
> 결정 요약 페이지: `/Users/hyunsuko/projects/work-flow/.archify/explainer-claude-workflow-20261103-083155/claude-workflow-review.html`
> 확정 도식: `/Users/hyunsuko/projects/work-flow/.archify/workflow-claude-final-20261103-1010/claude-workflow-final.html`
> 작성일: 2026-11-03

결정은 모두 끝났다. 다시 묻지 말고 구현한다. 막히는 결정이 생기면 이 탭에서 사용자에게 직접 묻는다.
진행은 아래 체크리스트를 체크해서 남긴다. work-flow 세션은 이 파일의 체크 상태로 진행을 판단한다.

## 이미 끝난 것 (건드리지 말 것)

- `task-plan` · `implement` · `qa` 스킬 삭제 (git에 삭제 스테이징됨), 참조 정리
- `tracker`가 `/flow`를 보내도록 수정 (아래 7번에서 tracker 자체를 지운다)
- `README.md`, `install.sh`, `.claude/CLAUDE.md`, `_shared/README.md`, `git-pr/references/resolution.md`, `browse/SKILL.md` 수정
- 이 변경은 `feat/flow-skill` 브랜치에 커밋 안 된 상태로 있다. 되돌리지 않는다. 기존 flow 미커밋 변경도 그대로 둔다.

## 결정 요약

- 스킬은 `/flow` 하나. 진입 판정 규칙(`~/AGENTS.md` Task Planning Rules)이 요청에서 경로를 고른다: PRD·Figma나 여러 화면·파일 → `/flow`, 여러 Jira 스토리 → flow 기능 문서, 그 외 → 바로 수정.
- tracker는 없앤다. 관제는 '보기·판단'만 남기고(flow 기능 문서 + Agent Control 앱), 세션끼리 메시지로 일을 시키는 '지시'는 버린다.
- 메타 플랜(`docs/<name>/meta-plan.md`)은 flow의 **기능 문서**로 바꾼다.
- 생성물(HTML · `share/` · `.receipts/`)은 커밋하지 않는다. Figma 캡처와 좌표 메타데이터(`.xml`)는 커밋한다.

## 체크리스트

### 1. flow 기능 문서 (메타 플랜 대체) — R6·R7

- [x] 기능 문서 JSON 형식 정의: 기획서 링크·스냅샷, 기획 섹션 → 스토리 → `[프론트]` 이슈 → 브랜치·워크트리 → flow 작업 id 표, 범위 간 공유물, 공유 컴포넌트 차이, 남은 질문, 기록. tracker `templates/meta-plan.template.md`의 항목이 출발점
- [x] 각 줄의 진행도는 그 줄의 flow 작업 JSON(단계 status, 항목 done)에서 계산한다. 손으로 적지 않는다
- [x] 기능 페이지 렌더링. 작업 페이지에서 위로 올라가면 기능 페이지. 기획 섹션 × 작업 인용 표에서 주인 없는 섹션, 스냅샷에 없는 섹션을 표시 (예시: `/Users/hyunsuko/projects/work-flow/.archify/example-tracker-replacement-20261103-1130/index.html` Q2·Q3)
- [x] 진입: 기획서 + 여러 스토리 링크가 오면 기능 문서 **초안**을 쓰고 페이지를 열고 멈춘다. 사용자가 승인하면 같은 턴에 2번의 `flow.py start`를 실행한다
- [x] tracker의 기획서 스냅샷 규칙(가져온 마크다운을 커밋, `last_edited_time` 기록, 사용자가 원할 때만 다시 받아 diff)을 기능 문서로 옮긴다

### 2. `flow.py start` — R6 Q1, R7 Q2

- [x] 승인된 기능 문서의 줄마다: Jira `[프론트]` 하위 이슈 생성(`acli`, `_shared/jira/md_to_adf.py`, 이미 있으면 재사용), orca 최상위 워크트리(`--no-parent` 후 `orca worktree list --json`으로 상위 없음 확인), 브랜치 `feat/<KEY>`(upstream 해제), flow 작업 뼈대(`branch`를 정확히 채움, links에 기획서·Figma·Jira)
- [x] 판단은 하지 않는다. 승인된 줄만 만들고 결과를 기능 문서에 쓴다
- [x] 루트 브랜치 규칙: `origin/<root>`에서 따고 루트에는 커밋·푸시 안 함

### 3. Jira — R6 Q5

- [x] 구현 단계 시작 시 이슈를 '작업 중'으로 전환(전환은 한 단계씩, 경로는 기능 문서에 기록)
- [x] 완료 단계에서 완료 댓글(tracker `templates/done-comment.template.md` 이동)
- [x] '[DEV] 개발 완료'처럼 조건이 붙은 전환은 하지 않고 기능 문서에 '사람이 옮길 것'으로 표시

### 4. 훅이 부를 명령 — R6 Q4, R7 Q4

- [x] `flow.py current [<dir>]`: 현재 git 브랜치와 `branch`가 같은 flow 작업을 찾는다. 정확히 하나면 `brief` 머리말(작업 줄 + 단계 줄, 5줄 안팎)을 출력. 0개나 여러 개면 경고 한 줄만 출력(`이 브랜치에 맞는 flow 작업이 없음` / `여러 개: <id>, <id>`). flow 문서가 없는 저장소에서는 아무것도 출력하지 않고 exit 0
- [x] SessionStart 훅 등록(`~/.claude/settings.json`)은 work-flow 세션이 한다. 이 명령만 만든다

### 5. 검증 · 기록 — R1·R2·R3

- [x] 완료 단계에서 `/git-pr` 제안 전에 `/code-review`를 돌린다. 리팩터링은 리뷰가 지적한 것만
- [x] 짧은 수정 기록 명령: 고친 파일을 다룬 작업이 있으면(`flow.py find --path`) 그 작업에 후속 수정 한 줄(날짜, 내용, 커밋 SHA)
- [x] 생성물(HTML · `share/` · `.receipts/`) git 제외, `flow.py open`이 먼저 build
- [x] 끝난 작업은 결론과 결정만 남기고 질문 라운드·체크리스트 세부는 정리

### 6. SOT 맵 개선 — R4·R5 (예시: `/Users/hyunsuko/projects/work-flow/.archify/example-flow-mapping-20261103-0910/index.html`)

- [x] 화면 매핑: Figma 캡처에 번호 핀(좌표는 메타데이터 `.xml`에서 스크립트가 계산) + API → 정규화 함수(`file:line`) → 화면 요소 줄
- [x] 파라미터 상자: URL 쿼리·경로 파라미터·화면 이동 값 → UI → API 요청 값, 기본값·변환 규칙
- [x] 작업 경로 맵: 작업이 건드리는 경로만. 경로·시트는 스크립트 추출, API 열은 작업에서 확인한 것만

### 7. tracker 삭제 — 1~3이 끝난 뒤

- [x] `.claude/skills/tracker` 삭제, 템플릿 중 쓰는 것은 flow로 이동
- [x] 참조 정리: `README.md`, `install.sh`(제거 목록에 `tracker` 추가, Cursor용 AGENTS 블록), `.claude/CLAUDE.md`, `_shared/README.md`, `plan-format.md`, `git-pr`
- [x] 설치본 동기화: `~/dotfiles/claude/skills/`는 복사본이다(`flow`만 심볼릭 링크). 바꾼 스킬을 그쪽에도 반영

## 이 세션 범위 밖 (work-flow 세션이 처리)

- SessionStart 훅 등록, `~/AGENTS.md`의 rebase·공용 작업 절차와 진입 판정 문구 갱신
- Agent Control(`/Users/hyunsuko/projects/multi-agentic-dashboard`)의 기능별 묶음, Jira 상태, [새 세션] 버튼, 판단 경고
