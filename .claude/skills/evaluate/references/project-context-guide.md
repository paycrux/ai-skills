# 프로젝트 컨텍스트 수집 가이드

에이전트에 전달할 프로젝트 컨텍스트를 수집하는 절차.
아래 소스를 **순서대로** 탐색하며, 존재하는 항목만 수집한다.

## 1. 프로젝트 규칙

| 소스 | 수집 내용 |
|---|---|
| `CLAUDE.md` (프로젝트 루트) | 프로젝트 전반 규칙, 컨벤션 |
| `.claude/rules/*.md` | 상세 룰 파일 |
| `.cursorrules`, `.cursor/rules/*.md` | Cursor 규칙 (있을 때만) |
| `eslint.config.*`, `.eslintrc.*` | 린트 규칙 |
| `tsconfig.json` | TypeScript 설정 (strict, paths 등) |
| `.prettierrc*` | 포매팅 규칙 |

## 2. 프로젝트 구조 & 의존성

`package.json`에서 식별할 핵심 의존성:

| 항목 | 예시 |
|---|---|
| 프레임워크 | React / React Native / Next.js |
| 상태관리 | Redux Toolkit, Zustand, Recoil, Jotai |
| 스타일링 | styled-components, Tailwind, CSS Modules |
| 테스트 | Jest, Vitest, Testing Library |

## 3. 디렉토리 구조

`ls src/` 또는 `ls app/`으로 아키텍처 패턴 식별:
- feature-based / layer-based / hybrid

## 수집 결과 조합

수집한 정보를 `templates/project-context-block.md` 포맷에 맞춰 조합한 뒤,
**두 에이전트 프롬프트에 동일하게 포함**한다.
