# evaluate-engineering 에이전트 실행 가이드

## 역할
TypeScript/JavaScript 엔지니어링 레벨 코드 품질 평가.
순환 참조, 함수형 프로그래밍, 코드 구조, 호환성을 검사한다.

## 에이전트 정의 위치
`.claude/agents/evaluate-engineering.md` — 전체 평가 기준과 출력 포맷이 정의되어 있음.

## 프롬프트 구성

에이전트 실행 시 반드시 아래 3가지를 프롬프트에 포함:

1. **프로젝트 컨텍스트 블록** — `templates/project-context-block.md` 포맷으로 수집한 정보
2. **대상 파일 목록** — Step 2에서 결정한 파일 리스트
3. **태스크 플랜 경로** — 있으면 `docs/plans/<folder>/` 경로

## 프롬프트 예시

```
다음 파일들의 엔지니어링 품질을 평가해줘.

## Project Context
- Framework: React Native 0.76
- State management: Redux Toolkit + Redux-Saga
- Styling: styled-components
- TypeScript: strict: true
- Key rules: 순환참조 금지, FP 패턴 준수
- Directory structure: feature-based (src/features/)

## 대상 파일
- src/features/order/api/orderApi.ts
- src/features/order/utils/priceCalculator.ts

## 태스크 플랜
docs/plans/order-coupon/
```
