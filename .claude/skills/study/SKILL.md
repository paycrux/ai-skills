---
name: study
description: Write a study report from the current conversation. Analyzes the problem, approaches tried, why they failed, and the final solution as a learning document.
argument-hint: [file-path] [requirements]
---

# /study - Conversation-based Study Report

Writes a study report from the current conversation. Think of this as a **research document** — the goal is to deeply understand the technology and problem, not just log what happened.

## Argument Parsing

- `/study` — Save report as a new markdown file in `<project-root>/.claude/study/`
- `/study <file-path>` — Append report to the specified file (preserve existing content)
- `/study <requirements>` — Adjust report scope/perspective based on requirements, save to `<project-root>/.claude/study/`

Parse `$ARGUMENTS` to distinguish the 3 cases:

- If it looks like a file path (starts with `/`, `./`, `../`, `~`, or `@`, or contains file extensions like `.md`, `.txt`) → treat as file path (remove leading `@` if present)
- Other text → treat as requirements
- Empty → save to `<project-root>/.claude/study/`

## Default Save Location

When no file path is specified (both empty args and requirements-only args), save the report as a new markdown file:

- Path: `<project-root>/.claude/study/{topic-slug}.md`
- File name: descriptive kebab-case slug derived from the topic (e.g., `react-native-animation-reanimated.md`, `zustand-state-management.md`)
- If the file already exists, append to it following the "When Appending to a File" rules below

## Context-Aware Writing

Before writing, **read the target file first** (if appending). Analyze what's already documented:

- If foundational concepts are already well-explained → **only add the new case study/analysis**
- If the topic is new or the file doesn't exist → **write both the technical foundation AND the case study**

### When adding to an existing document:

1. Read the file and understand its structure (numbered sections, heading style, depth level)
2. Continue the existing numbering and style
3. Add only what's new — don't repeat concepts already covered
4. Connect the new case to existing concepts where relevant (e.g., "이전 섹션 4의 reset 문제와 동일한 원인")

### When writing a new document:

Write two parts:

**파트 1: 기술 기반 지식**

- 이 기술/개념이 무엇인지
- 핵심 API/메서드와 사용 예시, 시각적 다이어그램 (ASCII art로 스택/상태 다이어그램 작성)
- 일반적인 패턴과 각각의 사용 시점
- 빠른 참조를 위한 요약 테이블

**파트 2: 사례 분석** (아래 구조와 동일)

## Case Study Structure

```markdown
## {섹션 번호}. {주제} - {날짜}

> 배경: {어떤 문제를 해결하려 했는지, 1-2줄}

### 문제

{구체적인 증상과 플로우 다이어그램}

### 시도한 접근법

각 접근법에 대해:

#### 접근법 N: {방법명}

- **코드**: 핵심 코드 스니펫 (간결하게)
- **결과**: 어떤 일이 일어났는지
- **실패 원인**: 근본 원인 분석 (가장 중요!)

### 최종 해결책

- **방법**: {최종 선택한 접근법}
- **코드**: 핵심 코드
- **이것이 동작하는 이유**: 내부 메커니즘 설명

### 핵심 교훈

- 이 경험에서 배운 원칙 (3-5개)
- 다음에 유사한 상황을 만나면 어떻게 접근할 것인지
```

## Writing Principles

1. **"실패 원인"이 가장 중요** — 단순 나열이 아니라 내부 메커니즘의 근본 원인 분석
2. **최소한의 코드** — 핵심 부분만, 전체 코드가 아님
3. **논리적 순서, 시간순이 아님** — 유사한 접근법은 함께 묶기
4. **재사용 가능한 교훈** — 프로젝트 한정이 아닌 범용적 원칙
5. **사용자의 실제 결과를 존중** — "성능이 안 좋았다"고 하면 추측 없이 그대로 기록
6. **시각적 다이어그램 활용** — ASCII 스택/상태 다이어그램이 텍스트만으로는 불분명한 흐름을 명확하게 함
7. **기본 원리와 연결** — 단순히 "동작한다"가 아니라 프레임워크 레벨에서 왜 동작하는지 설명

## When Appending to a File

- Read existing file content first with Read tool
- Match the existing document's numbering, heading style, and depth
- Add new section after a `---` separator at the end
- Never modify existing content
