# evaluate-react 에이전트 실행 가이드

## 역할
React/React Native 프레임워크 레벨 코드 품질 평가.
hooks, 불변성, 컴포넌트 패턴, 렌더 성능, 보안을 검사한다.

## 에이전트 정의 위치
`.claude/agents/evaluate-react.md` — 전체 평가 기준과 출력 포맷이 정의되어 있음.

## 프롬프트 구성

에이전트 실행 시 반드시 아래 3가지를 프롬프트에 포함:

1. **프로젝트 컨텍스트 블록** — `templates/project-context-block.md` 포맷으로 수집한 정보
2. **대상 파일 목록** — Step 2에서 결정한 파일 리스트
3. **태스크 플랜 경로** — 있으면 `docs/plans/<folder>/` 경로

## 프롬프트 예시

```
다음 파일들의 React/RN 코드 품질을 평가해줘.

## Project Context
- Framework: React Native 0.76
- State management: Redux Toolkit + Redux-Saga
- Styling: styled-components
- TypeScript: strict: true
- Key rules: useEffect 의존성 필수, state 불변성 준수
- Directory structure: feature-based (src/features/)

## 대상 파일
- src/features/order/screens/OrderScreen.tsx
- src/features/order/hooks/useOrderForm.ts

## 태스크 플랜
docs/plans/order-coupon/
```
