# AI Skills

AI 엔지니어링을 더 효과적으로 하기 위한 skills, agents, rules 모음입니다.

## 설치

### 원라인 설치 (권장)

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash
```

실행하면 대화형으로 에디터(Claude Code / Cursor)와 설치 범위(Global / Project)를 선택합니다.

### 옵션 지정 설치

대화형 선택 대신, 옵션을 직접 지정할 수도 있습니다. 두 가지를 조합합니다:

**1) 에디터 선택** — 둘 중 하나를 필수로 지정합니다.

| 옵션       | 설명                   |
| ---------- | ---------------------- |
| `--claude` | Claude Code용으로 설치 |
| `--cursor` | Cursor용으로 설치      |

**2) 설치 범위** — 어디에 설치할지 선택합니다.

| 옵션        | 설치 경로                      | 적용 범위                                 |
| ----------- | ------------------------------ | ----------------------------------------- |
| `--global`  | `~/.claude/` 또는 `~/.cursor/` | 내 모든 프로젝트에 적용                   |
| `--project` | `./.claude/` 또는 `./.cursor/` | 현재 프로젝트에만 적용 (팀원과 공유 가능) |

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

### 추가 옵션

위 조합에 아래 옵션을 추가로 붙일 수 있습니다.

| 옵션            | 설명                                       | 언제 사용하나요?              |
| --------------- | ------------------------------------------ | ----------------------------- |
| `--update`      | 이미 설치된 파일을 최신 버전으로 덮어쓰기  | ai-skills가 업데이트되었을 때 |
| `--only <type>` | `skills`, `agents`, `rules` 중 하나만 설치 | 특정 항목만 필요할 때         |

이미 설치했는데 새 버전이 나왔을 때:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

skills만 따로 설치하고 싶을 때:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --only skills
```

agents만 업데이트하고 싶을 때:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --cursor --project --only agents --update
```

### 수동 설치

1. 레포를 클론합니다.
2. `.claude/` 디렉토리를 `~/.claude/` (전역) 또는 프로젝트 루트의 `.claude/` (프로젝트)에 복사합니다.
3. Cursor 사용 시: `.cursor/` 디렉토리로 복사하고, `install.sh --cursor`를 참고하여 AGENTS.md를 구성합니다.

---

## Skills

슬래시 커맨드(`/skill-name`)로 호출하는 워크플로우입니다.

### /task-plan

**작업 계획 수립 + 문서 생성**

5가지 문서를 작성해 구현 계획을 구체적으로 만듭니다.

| 문서        | 역할                                                 |
| ----------- | ---------------------------------------------------- |
| README.md   | 개발자·비개발자 간 의사소통용 — 무엇을 구현할지 명시 |
| findings.md | 코드베이스 탐색 결과 — 기술적 구현 사항 정리         |
| spec.md     | 도메인 로직 기술 명세                                |
| ui-spec.md  | UI 구현 명세                                         |
| tasks.md    | 구현 단계 명시                                       |
| progress.md | 구현 진행 상황 추적                                  |

```
/task-plan <이슈번호(선택)> <구체적인 내용>
```

- Claude Code: 새 기능이나 버그 수정을 상세히 설명하면 자동으로 `/task-plan` 사용 여부를 물어봅니다.
- Cursor: 반드시 명시적으로 `/task-plan`을 호출해야 합니다.

### /implement

**문서 기반 단계별 구현**

task-plan에서 생성한 문서(spec, tasks, findings, ui-spec)를 읽고, 단계별로 구현을 진행합니다.

```
/implement <task-folder-name>    # docs/plans/<task-folder-name>/ 참조
/implement                       # 상태가 "진행중"인 작업 자동 감지
```

구현 사이클: 단계별 접근 요약 → 사용자 승인 → 전문 에이전트 실행 → 진행 상황 업데이트

### /evaluate

**코드 품질 종합 평가 (5개 에이전트 병렬)**

5개 평가 에이전트를 병렬로 실행하여 코드 품질을 다각도로 평가합니다.

| 에이전트 | 평가 영역 |
| --- | --- |
| evaluate-react | React/RN 프레임워크 품질 |
| evaluate-engineering | TS/JS 엔지니어링 품질 |
| evaluate-a11y | 접근성 (WCAG 2.1 AA) |
| evaluate-security | 프론트엔드 보안 |
| evaluate-performance | 프론트엔드 성능 |

```
/evaluate                        # 최근 변경 파일 자동 감지
/evaluate <file-or-directory>    # 특정 파일/디렉토리 평가
/evaluate <task-folder-name>     # task-plan 기반 평가
```

### /study

**학습 보고서 작성**

개발 후 익히고 싶은 내용을 분석하여 학습 문서를 작성합니다. task-plan 문서와 함께 사용하면 더 효과적입니다.

```
/study <문서 혹은 요구사항>
```

### /test-case

**테스트 케이스 생성**

구현된 코드나 요구사항에서 테스트 케이스를 생성합니다. Happy path와 조합 상태를 커버합니다.

```
/test-case <문서 혹은 요구사항>
```

### /qa-guide

**QA 테스트 가이드 생성**

QA 팀에게 전달할 테스트 가이드를 문서로 작성합니다.

```
/qa-guide <문서 혹은 요구사항>
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

---

## Agents

코드 변경 시 자동으로 사용되는 전문 에이전트입니다. 직접 호출하지 않고, skills이나 CLAUDE.md 규칙에 의해 자동으로 선택됩니다.

### 구현 에이전트

| 에이전트              | 담당 영역                                                                     |
| --------------------- | ----------------------------------------------------------------------------- |
| implement-engineering | 타입/인터페이스, API 클라이언트, 유틸리티, 서비스, 상태관리 셋업, 데이터 변환 |
| implement-react       | 컴포넌트, 훅, 스타일링, 화면, 네비게이션, UI 상태 처리                        |

혼합 작업(데이터 레이어 + UI)인 경우 `implement-engineering` → `implement-react` 순서로 실행됩니다.

### 평가 에이전트

| 에이전트             | 담당 영역                                                                |
| -------------------- | ------------------------------------------------------------------------ |
| evaluate-docs        | task-plan 문서 품질 평가                                                 |
| evaluate-react       | React/React Native 코드 품질 평가 (안티패턴, 룰 위반, 성능 이슈)         |
| evaluate-engineering | TypeScript/JavaScript 엔지니어링 품질 평가 (함수형, 순환참조, 코드 구조) |
| evaluate-a11y        | 접근성 평가 (WCAG 2.1 AA, 시맨틱 HTML, ARIA, 키보드 네비게이션)          |
| evaluate-security    | 프론트엔드 보안 평가 (XSS, CSRF, 인증 토큰, 민감 데이터)                |
| evaluate-performance | 프론트엔드 성능 평가 (번들 크기, 렌더링 효율, 메모리 릭, 네트워크)       |

---

## Rules

프로젝트에 자동 적용되는 코딩 규칙입니다.

| 규칙             | 적용 대상                                                             |
| ---------------- | --------------------------------------------------------------------- |
| react-typescript | React + TypeScript 구현 시 (Hooks, 불변성, 컴포넌트 패턴, 성능, 타입) |
| frontend-design  | 디자인 레퍼런스 없이 UI를 직접 만들 때 (AI Slop 방지, 맥락 기반 선택) |

---

## 프로젝트 구조

```
.claude/
├── CLAUDE.md              # 프로젝트 규칙 (task planning, 구현, 세션 이어받기, PR)
├── agents/
│   ├── implement-engineering.md
│   ├── implement-react.md
│   ├── evaluate-docs.md
│   ├── evaluate-react.md
│   ├── evaluate-engineering.md
│   ├── evaluate-a11y.md
│   ├── evaluate-security.md
│   └── evaluate-performance.md
├── skills/
│   ├── task-plan/SKILL.md
│   ├── implement/SKILL.md
│   ├── evaluate/SKILL.md
│   ├── browse/SKILL.md
│   ├── qa/SKILL.md
│   ├── investigate/SKILL.md
│   ├── study/SKILL.md
│   ├── test-case/SKILL.md
│   ├── qa-guide/SKILL.md
│   └── skill-creator/SKILL.md
└── rules/
    ├── react-typescript.md
    └── frontend-design.md
```
