# Cursor 셋업 가이드

이 문서를 Cursor Agent에게 전달하면 프로젝트에 워크플로우를 자동 셋업합니다.

> **사용법**: Cursor Composer (Agent 모드)에서
> `@/path/to/ai-skills/CURSOR_SETUP_GUIDE.md 이 가이드에 따라 우리 프로젝트에 셋업해줘` 입력

---

## 셋업 결과 디렉토리 구조

```
프로젝트 루트/
├── AGENTS.md                          # Cursor가 자동으로 읽는 에이전트 규칙
├── .cursor/
│   ├── rules/
│   │   ├── react-typescript.mdc       # React/TS 구현 규칙
│   │   └── frontend-design.mdc        # 프론트엔드 디자인 규칙
│   ├── agents/                        # 전문 에이전트 정의
│   │   ├── evaluate-docs.md
│   │   ├── evaluate-engineering.md
│   │   ├── evaluate-react.md
│   │   ├── implement-engineering.md
│   │   └── implement-react.md
│   └── skills/                        # 워크플로우 정의
│       ├── task-plan/
│       │   ├── SKILL.md
│       │   └── templates/
│       │       ├── spec.template.md
│       │       ├── ui-spec.template.md
│       │       ├── findings.template.md
│       │       └── tasks.template.md
│       ├── evaluate/
│       │   └── SKILL.md
│       ├── implement/
│       │   └── SKILL.md
│       ├── qa-guide/
│       │   └── SKILL.md
│       ├── study/
│       │   └── SKILL.md
│       └── test-case/
│           ├── SKILL.md
│           └── templates/
│               └── test-cases.template.md
└── docs/
    └── plans/                         # 구현 계획 산출물 (git 공유)
```

---

## Cursor Agent 실행 지시

아래 Step 1~4를 순서대로 실행하세요.

**소스 디렉토리**: 이 파일(`CURSOR_SETUP_GUIDE.md`)이 위치한 디렉토리의 `.claude/` 폴더

### Step 1: skills 복사

소스의 `.claude/skills/` 내 모든 폴더와 파일을 프로젝트의 `.cursor/skills/`로 복사합니다.

복사 대상:
- `.claude/skills/task-plan/` → `.cursor/skills/task-plan/`
- `.claude/skills/evaluate/` → `.cursor/skills/evaluate/`
- `.claude/skills/implement/` → `.cursor/skills/implement/`
- `.claude/skills/qa-guide/` → `.cursor/skills/qa-guide/`
- `.claude/skills/study/` → `.cursor/skills/study/`
- `.claude/skills/test-case/` → `.cursor/skills/test-case/`

**주의: 파일 내용을 수정하지 말 것 — 그대로 복사**

### Step 2: agents 복사

소스의 `.claude/agents/` 내 모든 파일을 프로젝트의 `.cursor/agents/`로 복사합니다.

복사 대상:
- `.claude/agents/evaluate-docs.md` → `.cursor/agents/evaluate-docs.md`
- `.claude/agents/evaluate-engineering.md` → `.cursor/agents/evaluate-engineering.md`
- `.claude/agents/evaluate-react.md` → `.cursor/agents/evaluate-react.md`
- `.claude/agents/implement-engineering.md` → `.cursor/agents/implement-engineering.md`
- `.claude/agents/implement-react.md` → `.cursor/agents/implement-react.md`

**주의: 파일 내용을 수정하지 말 것 — 그대로 복사**

### Step 3: rules 생성

소스의 `.claude/rules/` 파일 내용을 읽고, Cursor 전용 `.mdc` 프론트매터를 붙여 `.cursor/rules/`에 생성합니다.

#### .cursor/rules/react-typescript.mdc

```
---
description: React + TypeScript 프론트엔드 구현 시 적용
globs: ["*.tsx", "*.ts"]
alwaysApply: false
---
```

위 프론트매터 뒤에 소스의 `.claude/rules/react-typescript.md` 전체 내용을 이어 붙입니다.

#### .cursor/rules/frontend-design.mdc

```
---
description: 디자인 레퍼런스 없이 UI를 직접 만들 때 적용
globs: ["*.tsx", "*.css", "*.scss"]
alwaysApply: false
---
```

위 프론트매터 뒤에 소스의 `.claude/rules/frontend-design.md` 전체 내용을 이어 붙입니다.

### Step 4: AGENTS.md 생성 (프로젝트 루트)

프로젝트 루트에 아래 내용으로 `AGENTS.md` 파일을 생성합니다.
**이미 AGENTS.md가 있으면 기존 내용 뒤에 추가합니다.**

```markdown
# AGENTS.md

## Task Planning

사용자가 새로운 기능 개발, 버그 수정 등 작업을 요청하면:
- "task-plan 스킬을 사용해서 작업 계획을 먼저 세울까요, 아니면 바로 진행할까요?" 를 먼저 물어본다
- 계획이 필요없다고 하면 → 바로 진행
- 계획 작성을 원하면 → .cursor/skills/task-plan/SKILL.md 를 읽고 그대로 따른다
- 사용자가 디자인 문서나 요구사항을 첨부하면 → 분석 후 스킬 플로우에 반영

## 구현 규칙

코드 변경 작업(구현, 수정, 버그 수정, 리팩토링 등)을 수행할 때 **반드시 전문 에이전트를 사용한다.**

### 에이전트 선택 기준

| 작업 유형 | 에이전트 파일 |
|-----------|--------------|
| 타입/인터페이스, API 클라이언트, 유틸, 서비스, 상태관리 셋업, 데이터 변환 | @.cursor/agents/implement-engineering.md |
| 컴포넌트, 훅, 스타일링, 화면, 네비게이션, UI 상태 | @.cursor/agents/implement-react.md |
| 혼합 (데이터 레이어 + UI) | implement-engineering 먼저 → implement-react 순차 실행 |

### 에이전트 없이 직접 수정하는 경우 (예외)
- 설정 파일 변경 (package.json, tsconfig.json, .env 등)
- 문서 파일 변경 (*.md)
- 단순 오타/네이밍 수정 (1-2줄)
- import 경로 수정
- lint/format 수정

## 사용 가능한 워크플로우

| 워크플로우 | 파일 | 용도 |
|-----------|------|------|
| task-plan | @.cursor/skills/task-plan/SKILL.md | 작업 계획 수립 + 문서 생성 |
| implement | @.cursor/skills/implement/SKILL.md | 문서 기반 단계별 구현 |
| evaluate | @.cursor/skills/evaluate/SKILL.md | 코드 품질 종합 평가 |
| qa-guide | @.cursor/skills/qa-guide/SKILL.md | QA 테스트 가이드 생성 |
| test-case | @.cursor/skills/test-case/SKILL.md | 테스트 케이스 생성 |
| study | @.cursor/skills/study/SKILL.md | 학습 보고서 작성 |

## 평가 에이전트

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| evaluate-docs | @.cursor/agents/evaluate-docs.md | task-plan 문서 품질 평가 |
| evaluate-react | @.cursor/agents/evaluate-react.md | React/RN 코드 품질 평가 |
| evaluate-engineering | @.cursor/agents/evaluate-engineering.md | TS/JS 엔지니어링 품질 평가 |

## Plan 저장 경로

모든 plan 문서는 `docs/plans/{task-name}/` 에 저장한다.

## Task-plan 문서 최신화

구현 중 task-plan의 원인 분석이나 접근 방식이 실제와 다르다고 판단되면:

1. 구현을 멈추고 사용자에게 먼저 확인: "원인이 X가 아니라 Y로 보입니다. 문서를 최신화할까요?"
2. 승인 시 아래 문서를 업데이트:
   - **findings.md** — 원인 분석 수정 (핵심 대상)
   - **tasks.md** — 변경된 원인에 맞게 구현 단계 수정
   - **progress.md** — 방향 변경 사유 및 경위 기록
3. README.md는 증상/요구사항 기술이므로 업데이트 대상 아님

## 세션 이어받기

진행 중인 작업이 있으면:
1. `docs/plans/` 에서 상태가 "진행중"인 작업의 progress.md를 읽는다
2. 현재 상태를 보고한 후 사용자 승인을 받고 이어서 진행한다

## PR 생성 규칙

PR 생성 시 task 폴더의 문서 5개를 모두 참조하여 작성한다:
- PR 제목에 지라 이슈 번호 포함 (README.md 참조)
- PR 본문: 개요(README) / 변경점(tasks + 변경 파일) / 리뷰 중점사항(findings 기술 결정)
```

---

## 셋업 완료 확인

모든 Step이 완료되면 아래를 확인하세요:

- [ ] `.cursor/skills/` — 6개 폴더 (task-plan, evaluate, implement, qa-guide, study, test-case)
- [ ] `.cursor/agents/` — 5개 파일
- [ ] `.cursor/rules/` — 2개 .mdc 파일
- [ ] `AGENTS.md` — 프로젝트 루트에 존재

---

## 사용 방법

Cursor Composer에서 Agent 모드로 전환한 후:

### task-plan 실행
```
task-plan 워크플로우에 따라 {작업 설명}에 대한 계획을 세워줘
```
→ AGENTS.md를 읽고 자동으로 .cursor/skills/task-plan/SKILL.md를 참조합니다.

### 직접 스킬 참조 (AGENTS.md가 동작하지 않을 때)
```
@.cursor/skills/task-plan/SKILL.md 이 가이드에 따라 {작업 설명} 계획을 세워줘
```

### 기존 plan 이어서 구현
```
@.cursor/skills/implement/SKILL.md docs/plans/{task-name}/ 구현 시작해줘
```

### 코드 품질 평가
```
@.cursor/skills/evaluate/SKILL.md docs/plans/{task-name}/ 평가해줘
```

### QA 가이드 생성
```
@.cursor/skills/qa-guide/SKILL.md docs/plans/{task-name}/ 기반으로 QA 가이드 생성해줘
```

### 테스트 케이스 생성
```
@.cursor/skills/test-case/SKILL.md docs/plans/{task-name}/ 기반으로 테스트 케이스 생성해줘
```

---

## .gitignore 설정

```gitignore
# .cursor/skills/, .cursor/agents/, .cursor/rules/ 는 git에 포함 (팀 공유)
# 아래는 제외할 항목
.cursor/settings.json
.cursor/mcp.json
```

---

## 참고

- `.cursor/rules/`의 .mdc 파일은 globs 패턴에 매칭되는 파일 작업 시 Cursor가 자동으로 적용
- `AGENTS.md`는 Cursor Agent가 매 세션 자동으로 읽음
- `.cursor/skills/`, `.cursor/agents/`는 Cursor의 공식 기능이 아닌 워크플로우 파일 저장소 — AGENTS.md에서 `@` 참조하여 사용
- 에이전트 파일에 포함된 Claude Code 전용 설정(frontmatter, Persistent Agent Memory 등)은 Cursor에서 무시됨 — 핵심 지시 내용은 동일하게 동작
