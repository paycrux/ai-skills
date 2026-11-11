# AI Skills

AI 엔지니어링을 더 효과적으로 하기 위한 skills와 rules 모음입니다.

## 설치

### 원라인 설치 (권장)

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash
```

실행하면 대화형으로 에디터(Claude Code / Cursor / Codex)와 설치 범위(Global / Project)를 선택합니다.

### 업데이트 (`ai-skills` CLI)

v0.5.0부터 최초 설치 시 `~/.ai-skills/repo`에 저장소가 영구 clone되고, 짧은 전역 커맨드 `ai-skills`가 함께 설치됩니다. 이후 업데이트는 매번 `curl | bash` 전체를 다시 받을 필요 없이 아래 한 줄이면 됩니다.

```bash
ai-skills update    # 저장소 pull → 기록된 설치 대상을 재설치(--update)
ai-skills version   # 로컬 설치 버전과 원격 최신 버전 비교
```

`ai-skills update`는 여러 에디터·프로젝트에 각각 설치한 경우 `~/.ai-skills/installs.json`에 기록된 모든 대상을 갱신 후보로 봅니다. 옵션 없이 실행하면 대상이 하나뿐이어도 매번 아래처럼 어떤 것을 업데이트할지 번호로 고르는 대화형 프롬프트가 뜹니다.

```
업데이트할 대상을 선택하세요:
  1) claude (global) → ~/.claude
  2) cursor (project) → ./.cursor
  3) codex (global) → ~/.codex
  a) 전체
> (예: 1 3, 또는 a)
```

프롬프트 없이 특정 대상만 지정하고 싶다면 필터 플래그를 붙입니다.

| 옵션        | 설명                                  |
| ----------- | ------------------------------------- |
| `--claude`  | claude로 설치된 대상만 업데이트       |
| `--cursor`  | cursor로 설치된 대상만 업데이트       |
| `--codex`   | codex로 설치된 대상만 업데이트        |
| `--all`     | 확인 없이 기록된 모든 대상 업데이트   |

```bash
ai-skills update --claude          # Claude Code 대상만
ai-skills update --cursor --codex  # Cursor + Codex 대상만
ai-skills update --all             # 전부, 프롬프트 없이
```

에이전트(Claude Code / Cursor / Codex)와 무관한 순수 셸 도구입니다.

#### 새 에디터 추가 설치 (`ai-skills install`)

이미 `ai-skills`를 설치해뒀고, 다른 에디터(예: Cursor)를 추가로 설치하고 싶을 때 `curl | bash`를 다시 받을 필요 없이 아래처럼 씁니다.

```bash
ai-skills install    # 어떤 에디터·어떤 범위에 설치할지 대화형으로 선택
```

옵션 없이 실행하면 `install.sh`의 기존 대화형 선택(에디터 → 범위)으로 바로 들어갑니다.

```
Which editor?
  1) Claude Code
  2) Cursor
  3) Codex
> 2

Install scope?
  1) Global  (~/.cursor/) — all projects
  2) Project (./.cursor/) — current project only
> 1
```

스크립트에서 프롬프트 없이 바로 실행하고 싶다면 `install.sh`와 동일한 플래그를 그대로 붙일 수 있습니다.

```bash
ai-skills install --cursor --global
ai-skills install --codex --project --only skills
```

> 최초 설치 직후에는 셸이 아직 rc를 다시 읽지 않아 `ai-skills`가 잡히지 않을 수 있습니다. 새 터미널을 열거나 `source ~/.zshrc`(또는 `~/.bashrc`)를 실행하세요. zsh/bash가 아닌 셸은 안내에 따라 `export PATH="$HOME/.ai-skills/bin:$PATH"`를 직접 등록하면 됩니다.

CLI가 아직 등록되지 않은 환경(또는 최초 설치)에서는 기존 방식도 그대로 동작합니다:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

### 옵션 지정 설치

대화형 선택 대신, 옵션을 직접 지정할 수도 있습니다. 두 가지를 조합합니다:

**1) 에디터 선택** — 둘 중 하나를 필수로 지정합니다.

| 옵션       | 설명                   |
| ---------- | ---------------------- |
| `--claude` | Claude Code용으로 설치 |
| `--cursor` | Cursor용으로 설치      |
| `--codex`  | Codex용으로 설치       |

**2) 설치 범위** — 어디에 설치할지 선택합니다.

| 옵션        | 설치 경로                                     | 적용 범위                                 |
| ----------- | --------------------------------------------- | ----------------------------------------- |
| `--global`  | `~/.claude/`, `~/.cursor/`, `~/.codex/`       | 내 모든 프로젝트에 적용                   |
| `--project` | `./.claude/`, `./.cursor/`, `./.codex/`       | 현재 프로젝트에만 적용 (팀원과 공유 가능) |

**조합 예시:**

Claude Code + 전역 (가장 일반적):

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global
```

Claude Code + 현재 프로젝트만:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --project
```

Cursor + 전역:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --cursor --global
```

Cursor + 현재 프로젝트만:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --cursor --project
```

Codex + 전역:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --codex --global
```

> Codex는 `~/.codex/`(전역) 또는 `./.codex/`(프로젝트)에 skills·rules를 복사하고, Codex가 읽는 `AGENTS.md`(전역은 `~/.codex/AGENTS.md`, 프로젝트는 루트)에 스킬 참조를 병합합니다. Cursor와 달리 rules는 `.mdc`가 아닌 일반 `.md`로 설치됩니다.

### 추가 옵션

위 조합에 아래 옵션을 추가로 붙일 수 있습니다.

| 옵션            | 설명                                       | 언제 사용하나요?              |
| --------------- | ------------------------------------------ | ----------------------------- |
| `--update`      | 이미 설치된 파일을 최신 버전으로 덮어쓰기  | ai-skills가 업데이트되었을 때 |
| `--only <type>` | `skills`, `rules`, `docs` 중 하나만 설치   | 특정 항목만 필요할 때         |

skills만 따로 설치하고 싶을 때:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --only skills
```

### 수동 설치 (개발 시 테스트)

스킬을 수정하고 바로 테스트하고 싶을 때는 `--local` 플래그를 사용합니다. git clone 없이 현재 로컬 `.claude/`를 소스로 사용합니다.

```bash
# 전역 설치 (모든 프로젝트에 적용)
bash install.sh --claude --global --local

# 현재 프로젝트에만 설치
bash install.sh --claude --project --local

# 이미 설치된 상태에서 변경사항 반영
bash install.sh --claude --global --local --update
```

### v0.3.x → v0.4.0 업데이트

v0.4.0에서 서브에이전트 아키텍처가 제거되었습니다. `--update` 플래그로 설치하면 레거시 에이전트 파일이 자동으로 정리됩니다.

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

제거되는 파일:
- `agents/implement-engineering.md`, `agents/implement-react.md`
- `agents/evaluate-*.md` (6개)

---

## Skills

슬래시 커맨드(`/skill-name`)로 호출하는 워크플로우입니다.

### /flow

기획서와 Figma 링크를 받아 화면 하나를 PR까지 끌고 가는 흐름입니다. 문서는 화면 묶음(도메인)마다 폴더 하나에 JSON으로 쌓이고, `flow.py build`가 서로 링크된 HTML 페이지로 만듭니다. 서버 없이 파일을 더블클릭해서 열고, 파일 그대로 공유할 수 있습니다.

```
01 기획 → 02 화면 · SOT 맵 → 03 질문 → 04 구현 계획 · 구현 → 05 검증 → 06 완료
```

```
docs/
├ index.html             모든 기능 · 도메인과 진행 중인 작업 (생성)
├ features/gift/         기능 문서 — 기획서 하나가 지라 스토리 여러 개에 걸칠 때
│ ├ feature.json         기획 섹션 → 스토리 → [프론트] 이슈 → 브랜치 · 워크트리 → flow 작업
│ ├ prd.md               기획서 스냅샷 (커밋)
│ └ index.html           기능 페이지 (생성)
├ gift/                  도메인 = Figma 최상위 섹션 하나
│ ├ domain.json          이름, Figma 노드, 소스 경로 (새 작업이 어느 도메인인지 찾는 기준)
│ ├ screens.json         SOT 맵 — 화면 요소마다 값이 어느 서버 필드에서 오는지
│ ├ tasks/APP-452.json   작업 하나 = 파일 하나 (01~06 단계)
│ ├ images/
│ ├ index.html           작업 목록 + SOT 맵 (생성)
│ └ APP-452/             index.html + 01-plan.html … 06-done.html (생성)
└ (그 밖의 문서)         레거시 — 첫 페이지에 목록만
```

- **도메인당 폴더 하나**: 같은 화면의 후속 · 버그 · 문구 수정은 새 폴더를 만들지 않고 그 도메인의 `tasks/`에 파일만 추가합니다. 작업마다 파일이 따로라 여러 브랜치에서 동시에 작업해도 합칠 때 충돌하지 않습니다.
- **페이지**: 단계마다 HTML 파일이 하나씩이고, 왼쪽 목록에서 단계 사이를 오갑니다. 스타일과 스크립트가 파일 안에 들어 있어서 설치할 것이 없습니다. 페이지는 JSON에서 생성되므로 손으로 고치지 않습니다.
  - 저장소마다 `docs/flow.config.json`으로 모양을 바꿀 수 있습니다. `style`에 CSS 파일을 지정하면 기본 스타일 위에 덮어쓰고, `hide`에 적은 페이지 · 블록 · 질문 칸만 숨깁니다. 숨길 것만 적기 때문에 flow에 새 칸이 생기면 기본으로 보입니다. JSON 원본은 그대로입니다.
- **참조**: `[[S5]]`(SOT 행) · `[[R2-Q1]]`(질문) · `[[APP-451#P2]]`(다른 작업) · `[[login/S3]]`(다른 도메인)처럼 ID로 가리킵니다. 마우스를 올리면 내용이 보이고, 누르면 그 페이지의 그 자리로 이동합니다.
- **페이지에서 답하기**: 질문에 답하고 체크하면 그 브라우저의 `localStorage`에 자동으로 저장됩니다. 채팅에 "답 썼어"라고 하면 Claude가 `flow.py pull`로 브라우저 저장 파일을 직접 읽어 JSON에 반영하고, 확정된 내용을 다시 HTML로 만듭니다.
  - Chrome 계열(Chrome · Aside · Arc · Dia · Edge · Brave)만 직접 읽을 수 있습니다. Safari · Firefox에서는 페이지에 안내가 뜨고, '답 복사'를 누른 뒤 "복사했어"라고 하면 Claude가 클립보드를 읽습니다. 복사한 텍스트는 슬랙에 그대로 붙여도 읽기 좋은 형식입니다.
- **이전 버전 문서**: 서버를 쓰던 버전(`docs/.flow/`)과 작업 폴더 버전(`docs/<작업>/data/`)의 문서는 이 버전으로 `/flow`를 처음 실행할 때 `flow.py migrate`로 전부 옮깁니다. 서버 버전 파일은 지울 목록과 새로 여는 경로를 먼저 보여 주고, 사용자가 동의한 뒤 `--apply`로 지웁니다.
- **Claude가 읽는 양**: 이어받을 때는 `flow.py brief`(단계 상태 · 결론 · 결정)만 읽습니다. 예시 작업 기준 약 2KB.
- `scripts/flow.py`: `find`(도메인 찾기) · `domain` · `task` · `add`(단계 추가) · `build`(HTML 생성) · `pull`(답 가져오기) · `brief` · `changes`(사람이 바꾼 것) · `clear` · `check`(형식 · 참조 · HTML 최신 여부 검사) · `migrate` · `merge-xml`(Figma 컴포넌트 안쪽 좌표 합치기) · `open` · `current` · `log` · `prune` · `routes` · `feature` · `start` · `jira`
- **생성물은 커밋하지 않습니다**: 페이지 · `share/` · `.receipts/`는 `flow.py build`가 `docs/.gitignore`에 적어 둡니다. 새로 받은 체크아웃에서는 `flow.py open <페이지>`가 먼저 build하고 엽니다. JSON, 기획서 스냅샷, Figma 캡처와 좌표 XML은 커밋합니다.
- **기능 문서**: 기획서 + 지라 스토리 여러 개가 오면 기능 문서 초안을 쓰고 기능 페이지를 연 뒤 멈춥니다. 승인하면 `flow.py start`가 줄마다 `[프론트]` 하위 이슈, orca 최상위 워크트리, `feat/<키>` 브랜치(upstream 없음, `origin/<루트>`에서), flow 작업 뼈대를 만듭니다. 판단은 하지 않고 승인된 줄만 만듭니다. 기능 페이지의 진행도는 각 줄의 flow 작업에서 읽고, 아무 작업도 인용하지 않는 기획 섹션과 스냅샷에 없는 섹션을 노란 줄로 보여 줍니다. 예전 `/tracker`를 대신합니다 — 세션끼리 메시지로 일을 시키는 부분은 없앴습니다.
- **지라**: 구현을 시작할 때 `flow.py jira <작업> start`가 '작업 중'까지 한 단계씩 옮기고, 완료 단계에서 `done`이 완료 댓글을 단 뒤 옮깁니다. '[DEV] 개발 완료'처럼 개발계 배포가 필요한 전환은 하지 않고 기능 페이지에 '사람이 옮길 것'으로 표시합니다.
- **세션 시작**: `flow.py current`는 지금 브랜치와 `branch`가 같은 작업의 요약 머리말을 출력합니다(SessionStart 훅용). 맞는 작업이 없거나 여럿이면 경고 한 줄, flow 문서가 없는 저장소에서는 아무것도 출력하지 않습니다.
- **완료 뒤**: PR 제안 전에 `/code-review`를 돌리고 지적된 것만 고칩니다. 끝난 작업의 파일을 바로 고치면 `flow.py log`가 그 작업에 후속 수정 한 줄(날짜 · 내용 · 커밋)을 남기고, `flow.py prune`은 끝난 작업에서 결론과 결정만 남깁니다. 정리 시점은 05 완료에서 `/code-review` → 크리티컬 수정 → 테스트 재통과(검증 단계가 있으면 그것까지) → PR 여부 기록이 모두 끝난 순간입니다. 구현만 끝난 작업은 완료가 아니라 진행 중으로 보이고 정리되지 않습니다. 정리하지 않은 끝난 작업은 `flow.py check`가 실패로, `flow.py current`가 세션 시작 때 알려 줍니다.
- **SOT 맵**: 화면마다 들어오는 길, API → 정규화 함수(`file:line`) → 화면 요소 상자, URL 쿼리 · 경로 파라미터 · 화면 이동 값 → UI → API 요청 값 상자를 그립니다. `flow.py routes`는 작업이 건드리는 경로와 시트만 앱 디렉터리에서 뽑습니다.
- SOT 맵 방법론은 앱 저장소에서 쓰던 `sot-map` 스킬에서 가져왔습니다.

```bash
/flow <기획서 링크> <Figma 링크> <지라 키>
/flow <작업 ID>               # 이어서 진행
flow.py open docs/index.html  # build 후 문서 보기
```

`/task-plan`·`/implement`·`/qa`·`/tracker`는 `/flow`로 합쳐져 삭제되었습니다. `/tracker`가 쓴 `docs/<name>/meta-plan.md`는 읽기 전용입니다. 그 스킬들이 남긴 `tasks.html`·`spec.html` 계획은 읽기 전용이고, 첫 페이지에 레거시로 나열됩니다.

### /study

**학습 보고서 작성**

개발 후 익히고 싶은 내용을 분석하여 학습 문서를 작성합니다. `/flow` 작업 문서와 함께 사용하면 더 효과적입니다.

```
/study <문서 혹은 요구사항>
```

### /create-prd

**대형 문서 분할**

큰 마크다운 문서(로컬 파일 또는 Notion URL/page ID)를 H2 제목 기준으로 분할해 `docs/<name>/prd/`에 섹션별 파일과, 각 파일로 링크된 `0-overview.md`를 생성합니다. Notion 소스는 `notion-cli`로 먼저 마크다운으로 가져온 뒤 분할합니다(가져오기 스크립트는 `/notion-do`와 공유 — `skills/_shared/notion/`).

```
/create-prd <마크다운 파일 경로 또는 Notion URL/page ID>
```

### /notion-do

**Notion 문서 읽고 임의 작업 수행**

`notion-cli`로 Notion 링크를 읽어온 뒤, 요약·필드 추출·질문 답변·포맷 변환·번역·체크리스트 작성 등 사용자가 요청하는 작업을 자유롭게 수행합니다.

```
/notion-do <notion-url-or-page-id> <하고 싶은 작업>
```

### /skill-report

**스킬 버그 · 불편을 GitHub 이슈로 올림** — 별도 세션(`claude -p` 또는 `codex exec`, 읽기 전용)이 이슈 내용을 쓰고 스크립트가 `gh`로 올리며, 지금 세션엔 URL 한 줄만 돌아옵니다.

설치: ai-skills를 설치하면 함께 들어옵니다(이미 설치했다면 `ai-skills update`). 추가로 필요한 것은 두 가지입니다.

```bash
claude --version   # 또는 codex --version — 둘 중 설치된 것으로 새 세션을 띄움 (둘 다 있으면 claude, SKILL_REPORT_AGENT=codex로 지정)
gh auth login      # paycrux/ai-skills에 이슈를 올릴 GitHub 계정
```

```
/skill-report flow 승인 후에 매번 다시 물어봐서 불편해
```

### /browse

**헤드리스 브라우저 탐색/테스트**

헤드리스 브라우저로 웹 앱을 탐색, 테스트, 스크린샷 촬영합니다. Playwright Chromium 기반.

```
/browse <URL>                    # URL 탐색
/browse                          # 대화형 모드
```

- **테스트·QA·검증은 browse로만** 합니다. 호스트에 다른 브라우저 도구(Claude Code의 `claude-in-chrome`, Playwright/Puppeteer MCP)가 있어도 섞어 쓰지 않습니다 — 쿠키·세션·`@e` ref·`snapshot -D` 기준점이 갈라지면 diff와 재현 단계가 무의미해지기 때문입니다.
- 공개 문서 한 페이지 읽기 같은 곁가지 조회는 호스트 기본 도구를 쓰세요. 그것 때문에 browse 서버를 띄울 이유는 없습니다.

### /git-pr

**Git 브랜치 작업 + PR 생성 통합 워크플로우**

브랜치 생성/푸시부터 PR 생성까지 하나의 스킬에서 처리합니다. 커밋 로그와 diff를 분석해 PR 제목과 본문 초안을 자동으로 작성하고 사용자가 확인 후 생성합니다.

사용자가 `/git-pr`을 직접 입력하지 않아도 Claude가 부를 수 있습니다. "PR 올려줘"라고 하거나 `/flow` 05 완료에서 PR을 만들겠다고 답하면 Claude가 실행하고, 초안을 보여 준 뒤 확인을 받고서야 PR을 만듭니다. 브랜치가 `/flow` 작업 JSON을 바꿨으면 그 경로를 본문 첫 줄에 링크하고, flow가 이미 `/code-review`를 돌렸으면 리뷰 제안을 건너뜁니다.

초안을 보여주기 전에 **변경사항 리뷰를 한 번 제안**합니다. Claude Code에서는 빌트인 `/code-review`(인증·권한·결제·시크릿이 걸리면 `/security-review`까지)를 호출하고, Cursor·Codex에서는 diff를 직접 읽어 체크리스트로 리뷰합니다. 리뷰는 PR 생성을 막지 않고, 결과가 PR 본문에 들어가지도 않습니다 — 본문은 diff에서 확인되는 사실만 담습니다.

```
/git-pr                          # 대화형 모드 (브랜치 방식 + PR 여부 선택)
/git-pr --mode git               # 브랜치 작업만
/git-pr --mode pr                # PR 생성만 (현재 브랜치 기준)
/git-pr --mode both              # 브랜치 작업 + PR 생성
/git-pr --new <branch-name>      # 새 브랜치 생성 모드
/git-pr --suffix dev             # 현재 브랜치에 -dev 서브 브랜치 생성
/git-pr --issue ABC-123          # PR 제목 앞에 붙일 이슈 번호 직접 지정
/git-pr --review                 # 확인 없이 PR 생성 전 리뷰 실행
/git-pr --no-review              # 리뷰 단계 건너뛰기
/git-pr --no-issue               # 이슈 번호 없이 제목만 사용
/git-pr --shots both             # 구현 화면 Before + After 촬영 (after: After만, none: 촬영 안 함)
```

PR 제목은 `[이슈번호] 요약` 형태로 생성됩니다. 이슈 번호는 `--issue` → `tasks.md` 헤더의 `> 이슈:` → 브랜치명의 Jira 키(`feature/ABC-123-login`) 순으로 찾고, 어디에도 없으면 직접 입력할지 생략할지 물어봅니다.

PR 본문 구성:

| 섹션 | 작성 주체 | 출력 조건 |
| --- | --- | --- |
| 변경사항 | Claude 자동 생성 | 항상 |
| 구현 화면 | 스크린샷 촬영 시 Claude가 채움, 건너뛰면 사용자 직접 추가 | UI 변경이 있을 때만 |

`변경사항`은 커밋 순서가 아니라 **사용자가 체감하는 기능/시나리오 단위로 묶어** 소제목을 만듭니다. 조건을 만족하지 않는 섹션은 "없음"을 쓰지 않고 제목째 삭제되므로, 내용 없는 항목이 PR에 남지 않습니다.

노이즈를 줄이기 위한 작성 규칙(`SKILL.md`의 R1–R7):

- diff로 확인 가능한 사실만 기록 — 의도·기대효과 추측 금지, "전반적으로 개선" 같은 빈 문장 금지
- 백틱은 식별자(경로·함수명·명령어·환경변수)에만. 한글 설명문을 백틱으로 감싸지 않음
- 그룹당 불릿 5개 상한
- 산문과 불릿만 사용 — mermaid·ASCII 아트 금지. 이미지는 `구현 화면` 표의 스크린샷만. 불릿으로 설명이 안 되면 그룹을 쪼갠다

**구현 화면 스크린샷** — UI가 바뀐 PR이면 촬영할지 묻고, 찍기로 하면:

- 모바일(RN/Expo)은 부팅된 iOS 시뮬레이터·연결된 Android 기기에서 딥링크로 화면을 열어 찍음(`scripts/shot-mobile.sh`). After는 라이트/다크 두 벌
- 웹은 `/browse` 헤드리스 브라우저로 찍음. 프로젝트에 다크 모드가 있으면 다크도
- Before는 따로 물어봄. 찍기로 하면 base 브랜치 코드로 잠깐 전환해 찍고 원래 브랜치로 돌아옴. 네이티브 코드·의존성이 바뀐 브랜치는 자동 반영이 안 돼서 Before를 건너뜀
- 찍은 칸은 전부 채우고, 실패한 칸만 비운 뒤 이유를 알려줌
- 이미지는 `gh attach`로 올림. 업로드하려면 PR이 먼저 있어야 해서 draft로 만들고, 이미지를 채운 뒤 공개(`gh pr ready`)하므로 이미지 없는 PR이 리뷰어에게 보이지 않음
- 모바일 앱의 딥링크 scheme·번들 ID는 처음 한 번 `app.json`에서 읽거나 물어보고 `.git/git-pr-shot.env`에 저장(커밋되지 않음, 워크트리끼리 공유)

관련 템플릿: `.claude/skills/git-pr/templates/` (`pr-body.template.md`, `pr-body.example.md`)

### /skill-creator

**스킬 생성/리팩토링**

새로운 Claude Code 스킬을 스캐폴딩하거나, 기존 스킬을 리팩토링/리뷰합니다.

```
/skill-creator <new-skill-name>       # 새 스킬 생성
/skill-creator <existing-skill-path>  # 기존 스킬 리팩토링
/skill-creator                        # 대화형 모드
```

---

## Docs

프로젝트별 UI 패턴 레퍼런스 문서입니다. `/flow`가 해당 화면의 구현 계획을 쓸 때 참고해, 항목의 `재사용`·`패턴` 행에 인라인합니다.

| 문서 | 적용 대상 |
| --- | --- |
| `partner-jirisan.md` | white_label admin/partner 앱의 DataTable 구현 |
| `partner-option-group-factory.md` | white_label admin/partner 앱의 검색 필터(Advanced Search) 구현 |

---

## Rules

프로젝트에 자동 적용되는 코딩 규칙입니다.

| 규칙             | 적용 대상                                                                                      |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| react-typescript | React + TypeScript 구현 시 (Hooks, 불변성, 렌더링, 컴포넌트 패턴, 메모이제이션, 타입)          |
| frontend-design  | 디자인 레퍼런스 없이 UI를 직접 만들 때 (AI Slop 방지, 맥락 기반 선택)                          |
| writing          | 사람이 읽는 산문을 쓸 때 (계획 문서, 진행 기록, PR 본문, QA 가이드, 대화 출력)                  |

> `writing` 룰은 `/flow`·`/skill-creator`가 각자 들고 있던 동일한 `Communication Style` 블록의 원본입니다. 각 스킬에는 한 문단 요약과 이 파일 링크만 남아 있으니, 규칙을 고칠 때는 `rules/writing.md`를 먼저 고치세요.

> `react-typescript` 룰에서 **렌더링**과 **메모이제이션**은 별개 카테고리입니다. 리렌더 이슈는 구조적 해결(분해/격리/상태 위치/key)을 먼저 시도하고, 메모이제이션 훅(`useMemo`/`useCallback`/`React.memo`)은 사용자가 명시적으로 요청할 때만 도입합니다.

---

## 프로젝트 구조

```
.claude/
├── CLAUDE.md              # 프로젝트 규칙 (task planning, 구현, 세션 이어받기, PR)
├── skills/
│   ├── browse/SKILL.md
│   ├── git-pr/
│   │   ├── SKILL.md
│   │   ├── references/    # resolution.md (이슈 번호·base 브랜치 해석), screenshots.md (구현 화면 촬영)
│   │   ├── scripts/       # shot-mobile.sh (iOS 시뮬레이터·Android 기기 캡처)
│   │   └── templates/     # pr-body.template.md, pr-body.example.md
│   ├── study/SKILL.md
│   ├── create-prd/SKILL.md
│   ├── notion-do/SKILL.md
│   ├── skill-report/      # SKILL.md, scripts/report.sh (새 세션 실행), templates/issue-body.md
│   ├── _shared/           # 스킬 아님 — 둘 이상이 쓰는 코드
│   │   ├── notion/fetch_notion_markdown.py
│   │   └── jira/md_to_adf.py
│   └── skill-creator/
├── docs/
│   ├── partner-jirisan.md
│   └── partner-option-group-factory.md
└── rules/
    ├── react-typescript.md
    ├── frontend-design.md
    └── writing.md
```
