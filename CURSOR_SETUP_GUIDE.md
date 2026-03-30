# Cursor 셋업 가이드

프로젝트 안에 AGENTS.md + .cursor/ 폴더로 task-plan 워크플로우를 셋업하는 방법.

## 프로젝트 디렉토리 구조

```
프로젝트 루트/
├── AGENTS.md                          # Cursor가 자동으로 읽는 에이전트 규칙
├── .cursor/
│   └── rules/
│       ├── react-typescript.mdc       # React/TS 구현 규칙
│       └── frontend-design.mdc        # 프론트엔드 디자인 규칙
├── .cursor/skills/                    # 스킬 파일 (워크플로우 정의)
│   ├── task-plan/
│   │   ├── SKILL.md
│   │   └── templates/
│   │       ├── README.template.md
│   │       ├── spec.template.md
│   │       ├── ui-spec.template.md
│   │       ├── findings.template.md
│   │       ├── tasks.template.md
│   │       └── progress.template.md
│   ├── qa-guide/
│   │   └── SKILL.md
│   └── test-case/
│       ├── SKILL.md
│       └── templates/
│           └── test-cases.template.md
└── docs/
    └── plans/                         # 구현 계획 산출물 (git 공유)
```

## 셋업 순서

### 1. .cursor/skills/ 에 스킬 파일 복사

프로젝트 루트에서:

```bash
mkdir -p .cursor/skills

# 스킬 파일을 전달받아 .cursor/skills/ 에 배치
# (팀 리드가 공유한 zip, git submodule, 또는 직접 복사)
cp -r task-plan .cursor/skills/
cp -r qa-guide .cursor/skills/
cp -r test-case .cursor/skills/
```

### 2. .cursor/rules/ 에 규칙 파일 생성

#### .cursor/rules/react-typescript.mdc

```markdown
---
description: React + TypeScript 프론트엔드 구현 시 적용
globs: ["*.tsx", "*.ts"]
alwaysApply: false
---

(react-typescript.md 내용 붙여넣기)
```

#### .cursor/rules/frontend-design.mdc

```markdown
---
description: 디자인 레퍼런스 없이 UI를 직접 만들 때 적용
globs: ["*.tsx", "*.css", "*.scss"]
alwaysApply: false
---

(frontend-design.md 내용 붙여넣기)
```

### 3. AGENTS.md 생성 (프로젝트 루트)

```markdown
# AGENTS.md

## Task Planning

사용자가 새로운 기능 개발, 버그 수정 등 작업을 요청하면:
- "task-plan 워크플로우로 작업 계획을 먼저 세울까요, 아니면 바로 진행할까요?" 를 먼저 물어본다
- 계획이 필요없다고 하면 → 바로 진행
- 계획 작성을 원하면 → .cursor/skills/task-plan/SKILL.md 를 읽고 그대로 따른다

## 사용 가능한 워크플로우

| 워크플로우 | 파일 | 용도 |
|-----------|------|------|
| task-plan | @.cursor/skills/task-plan/SKILL.md | 작업 계획 수립 + 문서 생성 |
| qa-guide | @.cursor/skills/qa-guide/SKILL.md | QA 테스트 가이드 생성 |
| test-case | @.cursor/skills/test-case/SKILL.md | 테스트 케이스 생성 |

## Plan 저장 경로

모든 plan 문서는 `docs/plans/{task-name}/` 에 저장한다.

## 세션 이어받기

진행 중인 작업이 있으면:
1. `docs/plans/` 에서 상태가 "진행중"인 작업의 progress.md를 읽는다
2. 현재 상태를 보고한 후 사용자 승인을 받고 이어서 진행한다

## PR 생성 규칙

PR 생성 시 task 폴더의 문서를 모두 참조하여 작성한다:
- PR 제목에 지라 이슈 번호 포함 (README.md 참조)
- PR 본문: 개요(README) / 변경점(tasks + 변경 파일) / 리뷰 중점사항(findings 기술 결정)
```

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
@docs/plans/{task-name}/tasks.md 이 문서의 Phase 1을 구현해줘
```

### QA 가이드 생성
```
@.cursor/skills/qa-guide/SKILL.md docs/plans/{task-name}/ 기반으로 QA 가이드 생성해줘
```

## .gitignore 설정

```gitignore
# .cursor/skills/ 는 git에 포함 (팀 공유)
# 아래는 제외할 항목
.cursor/settings.json
.cursor/mcp.json
```

## 참고

- `.cursor/rules/` 의 .mdc 파일은 globs 패턴에 매칭되는 파일 작업 시 Cursor가 자동으로 적용
- `AGENTS.md` 는 Cursor Agent가 매 세션 자동으로 읽음
- `.cursor/skills/` 는 Cursor의 공식 기능이 아닌 워크플로우 파일 저장소 — AGENTS.md에서 참조하여 사용
