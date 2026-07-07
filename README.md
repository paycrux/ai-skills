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

### /task-plan

**작업 계획 수립 + 문서 생성 (경량화 버전)**

작업 설명을 받아 `docs/{task-name}/plans/` 아래에 2개 문서를 작성합니다. 작업 종류(버그 수정 / 기능 개발 / 기능 수정)는 `tasks.md` 헤더 메타데이터로만 표시됩니다.

| 문서     | 역할                                                                 |
| -------- | -------------------------------------------------------------------- |
| tasks.md | 작업 종류·범위·Phase별 구현 단계 + 진행 기록 (탐색 결과 인라인)      |
| spec.md  | 도메인 로직 / 행동 명세                                              |

- 코드베이스 탐색 결과(재사용 컴포넌트, 라이브러리 패턴, 관련 파일)는 해당 Phase 항목의 sub-bullet로 인라인됩니다.
- Figma 노드는 task 라인에 인라인 링크로 표기됩니다.
- "기능 수정" 작업은 원본 plans에 `참조:` 헤더 링크만 추가하고, 원본 파일은 수정하지 않습니다.

```
/task-plan <이슈번호(선택)> <구체적인 내용>
```

- Claude Code: 새 기능이나 버그 수정을 상세히 설명하면 자동으로 `/task-plan` 사용 여부를 물어봅니다.
- Cursor: 반드시 명시적으로 `/task-plan`을 호출해야 합니다.

### /implement

**문서 기반 단계별 구현**

task-plan에서 생성한 문서(`tasks.md`, `spec.md`) 두 개를 읽고, 단계별로 직접 구현합니다. 서브에이전트 없이 메인 대화에서 코드를 작성합니다.

```
/implement <task-folder-name>    # docs/<task-folder-name>/plans/ 참조
/implement                       # tasks.md 헤더 상태가 "진행중"인 작업 자동 감지
/implement <task-name> phase 2   # 특정 Phase만 실행
```

구현 사이클: 단계별 접근 요약 → 사용자 승인 → 직접 구현 → `tasks.md` 체크박스 토글 + `## 진행 기록` 누적

- 진행 기록은 별도 `progress.md`가 아닌 `tasks.md`의 `## 진행 기록` 섹션에 누적됩니다.
- 전체 완료 시 `tasks.md` 헤더 `상태:` 필드가 `완료`로 변경됩니다.
- 렌더링 이슈는 구조(컴포넌트 분해 / 상태 위치 / key / 파생 값)로 먼저 해결합니다. `useMemo`/`useCallback`/`React.memo` 같은 메모이제이션 훅은 **사용자가 명시적으로 요청할 때만** 도입합니다.

### /study

**학습 보고서 작성**

개발 후 익히고 싶은 내용을 분석하여 학습 문서를 작성합니다. task-plan 문서와 함께 사용하면 더 효과적입니다.

```
/study <문서 혹은 요구사항>
```

### /qa-guide

**QA 테스트 가이드 생성**

task-plan의 `tasks.md` 안에 `## QA 가이드` 섹션을 작성합니다. 별도 파일을 만들지 않고 `tasks.md` 하나를 단일 소스로 유지합니다. `tasks.md` 헤더에 Jira 이슈 키가 있으면 `acli`로 해당 섹션을 이슈 설명에도 동기화합니다(acli 미설치/미로그인 시 자동 설치·로그인 없이 안내만 표시).

```
/qa-guide <문서 혹은 요구사항>
```

### /create-prd

**대형 문서 분할**

큰 마크다운 문서(로컬 파일 또는 Notion URL/page ID)를 H2 제목 기준으로 분할해 `docs/<name>/prd/`에 섹션별 파일과, 각 파일로 링크된 `0-overview.md`를 생성합니다. Notion 소스는 `notion-cli`로 먼저 마크다운으로 가져온 뒤 분할합니다.

```
/create-prd <마크다운 파일 경로 또는 Notion URL/page ID>
```

### /notion-do

**Notion 문서 읽고 임의 작업 수행**

`notion-cli`로 Notion 링크를 읽어온 뒤, 요약·필드 추출·질문 답변·포맷 변환·번역·체크리스트 작성 등 사용자가 요청하는 작업을 자유롭게 수행합니다.

```
/notion-do <notion-url-or-page-id> <하고 싶은 작업>
```

### /browse

**헤드리스 브라우저 탐색/테스트**

헤드리스 브라우저로 웹 앱을 탐색, 테스트, 스크린샷 촬영합니다. Playwright Chromium 기반.

```
/browse <URL>                    # URL 탐색
/browse                          # 대화형 모드
```

### /qa

**브라우저 기반 QA 검증**

task-plan 문서를 기반으로 헤드리스 브라우저로 구현 결과를 검증하고, 버그 리포트를 작성합니다.

```
/qa <task-folder-name>           # task-plan 기반 QA
/qa <URL>                        # URL 직접 검증
```

### /git-pr

**Git 브랜치 작업 + PR 생성 통합 워크플로우**

브랜치 생성/푸시부터 PR 생성까지 하나의 스킬에서 처리합니다. 커밋 로그와 diff를 분석해 PR 제목과 본문 초안을 자동으로 작성하고 사용자가 확인 후 생성합니다.

```
/git-pr                          # 대화형 모드 (브랜치 방식 + PR 여부 선택)
/git-pr --mode git               # 브랜치 작업만
/git-pr --mode pr                # PR 생성만 (현재 브랜치 기준)
/git-pr --mode both              # 브랜치 작업 + PR 생성
/git-pr --new <branch-name>      # 새 브랜치 생성 모드
/git-pr --suffix dev             # 현재 브랜치에 -dev 서브 브랜치 생성
```

PR 본문 구성:

| 섹션 | 작성 주체 |
| --- | --- |
| 구현사항 | Claude 자동 생성 |
| 특이사항 | Claude 자동 생성 |
| 핵심 리뷰 포인트 | Claude 자동 생성 |
| 구현 화면 | 사용자 직접 추가 |
| 테스트 케이스 | Claude 자동 생성 |

### /investigate

**체계적 디버깅 + 근본원인 분석**

증상 수집 → 가설 생성 → 검증 루프를 반복하여 근본 원인을 분석합니다. `/task-plan`보다 가벼운 디버깅 워크플로우.

```
/investigate <증상 또는 에러 메시지>
```

### /skill-creator

**스킬 생성/리팩토링**

새로운 Claude Code 스킬을 스캐폴딩하거나, 기존 스킬을 리팩토링/리뷰합니다.

```
/skill-creator <new-skill-name>       # 새 스킬 생성
/skill-creator <existing-skill-path>  # 기존 스킬 리팩토링
/skill-creator                        # 대화형 모드
```

### /caveman

**초압축 커뮤니케이션 모드**

응답을 caveman체로 압축해 출력 토큰을 65% 절감합니다 (관사/필러/공손 표현 제거, 기술 내용은 그대로 유지). `task-plan`/`implement`/`qa-guide`/`skill-creator`는 대화 응답과 산출물 자유서술 섹션에 이 스킬을 사용합니다.

```
/caveman            # full 모드 (기본)
/caveman lite        # 약한 압축
/caveman ultra       # 극단적 압축
/caveman wenyan      # 문언문(classical Chinese) 모드
stop caveman         # 일반 모드로 복귀
```

> [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (MIT License)에서 vendoring — 라이센스 전문은 `.claude/skills/caveman/LICENSE` 참고.

---

## Docs

프로젝트별 UI 패턴 레퍼런스 문서입니다. `/task-plan` 실행 시 Figma/디자인을 분석해 해당 패턴을 자동으로 감지하고 `ui-spec.md`에 embed합니다.

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

> `react-typescript` 룰에서 **렌더링**과 **메모이제이션**은 별개 카테고리입니다. 리렌더 이슈는 구조적 해결(분해/격리/상태 위치/key)을 먼저 시도하고, 메모이제이션 훅(`useMemo`/`useCallback`/`React.memo`)은 사용자가 명시적으로 요청할 때만 도입합니다.

---

## 프로젝트 구조

```
.claude/
├── CLAUDE.md              # 프로젝트 규칙 (task planning, 구현, 세션 이어받기, PR)
├── skills/
│   ├── task-plan/SKILL.md
│   ├── implement/SKILL.md
│   ├── browse/SKILL.md
│   ├── qa/SKILL.md
│   ├── git-pr/SKILL.md
│   ├── study/SKILL.md
│   ├── qa-guide/SKILL.md
│   ├── create-prd/SKILL.md
│   ├── notion-do/SKILL.md
│   ├── skill-creator/SKILL.md
│   └── caveman/SKILL.md
├── docs/
│   ├── partner-jirisan.md
│   └── partner-option-group-factory.md
└── rules/
    ├── react-typescript.md
    └── frontend-design.md
```
