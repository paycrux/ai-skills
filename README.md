# AI Skills

AI 엔지니어링을 더 효과적으로 하기 위한 skills와 rules 모음입니다.

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
| `--only <type>` | `skills`, `rules`, `docs` 중 하나만 설치   | 특정 항목만 필요할 때         |

이미 설치했는데 새 버전이 나왔을 때:

```bash
curl -fsSL https://raw.githubusercontent.com/paycrux/ai-skills/main/install.sh | bash -s -- --claude --global --update
```

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

task-plan에서 생성한 문서(spec, tasks, findings, ui-spec)를 읽고, 단계별로 직접 구현합니다. 서브에이전트 없이 메인 대화에서 코드를 작성합니다.

```
/implement <task-folder-name>    # docs/<task-folder-name>/ 참조
/implement                       # 상태가 "진행중"인 작업 자동 감지
```

구현 사이클: 단계별 접근 요약 → 사용자 승인 → 직접 구현 → 진행 상황 업데이트

### /evaluate

**체크리스트 기반 코드 품질 평가**

5개 도메인에 대해 코드를 직접 평가합니다:

| 도메인 | 평가 항목 |
| --- | --- |
| React / Accessibility | Hooks 규칙, 불변성, 키보드/ARIA, 색상 대비 |
| Engineering / Performance | 순환 참조, 코드 구조, DRY, 번들 크기, 렌더링 효율 |
| Security | XSS, injection, 인증/인가, 민감 데이터 |

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

### /finalize

**작업 문서 최종 정리**

구현, 평가, QA가 모두 끝난 후 호출합니다. 임시 문서(findings, tasks, progress, evaluate, qa-report, qa-guide)를 삭제하고, 구현 파일 매핑을 spec.md의 Implementation Map 섹션에 병합합니다.

```
/finalize <task-folder-name>    # 특정 작업 정리
/finalize                       # 완료된 작업 자동 감지
```

정리 후 남는 문서:

| 문서 | 역할 |
| --- | --- |
| README.md | 작업 개요/배경/목표 |
| spec.md | 행동 명세 + Implementation Map (파일 매핑, 기술 결정) |
| ui-spec.md | 컴포넌트 구조/상태 설계 (프론트엔드만) |
| test-cases.md | 반복 검증용 테스트 케이스 |

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

프로젝트별 UI 패턴 레퍼런스 문서입니다. `/task-plan` 실행 시 Figma/디자인을 분석해 해당 패턴을 자동으로 감지하고 `ui-spec.md`에 embed합니다.

| 문서 | 적용 대상 |
| --- | --- |
| `partner-jirisan.md` | white_label admin/partner 앱의 DataTable 구현 |
| `partner-option-group-factory.md` | white_label admin/partner 앱의 검색 필터(Advanced Search) 구현 |

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
├── skills/
│   ├── task-plan/SKILL.md
│   ├── implement/SKILL.md
│   ├── evaluate/SKILL.md
│   ├── browse/SKILL.md
│   ├── qa/SKILL.md
│   ├── finalize/SKILL.md
│   ├── investigate/SKILL.md
│   ├── study/SKILL.md
│   ├── test-case/SKILL.md
│   ├── qa-guide/SKILL.md
│   └── skill-creator/SKILL.md
├── docs/
│   ├── partner-jirisan.md
│   └── partner-option-group-factory.md
└── rules/
    ├── react-typescript.md
    └── frontend-design.md
```
