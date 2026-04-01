# React + TypeScript 구현 규칙

> 프론트엔드 구현 시 참조. 위반하면 런타임 버그 또는 유지보수 문제를 유발하는 규칙만 수록.

## Hooks

- 최상위에서만 호출 — 조건문, 반복문, 중첩 함수 안에서 호출 금지
- React 함수 컴포넌트 또는 커스텀 훅에서만 호출
- 커스텀 훅은 반드시 `use`로 시작
- `useEffect` 의존성 배열 수정 시 무한루프 방지가 최우선:
  - 함수/메서드/콜백은 의존성 배열에 추가 금지 (매 렌더마다 새 참조 → 무한루프)
  - 기존 배열을 전부 제거하고 새로 채우지 말 것 — 기존 유지하면서 필요한 것만 추가/제거
  - 모든 의존성을 빠짐없이 명시할 필요 없음
- cleanup이 필요한 `useEffect`는 반드시 cleanup 함수 반환 (타이머, 구독, AbortController)

## 불변성

- state를 직접 변경 금지 — 항상 새 참조 생성
  - 배열: `[...arr]`, `.map()`, `.filter()` 사용 — `.push()`, `.splice()`, `.sort()` on state 금지
  - 객체: `{ ...obj }` 사용 — `obj.key = value` on state 금지
- 중첩 상태 업데이트 시 모든 레벨에서 spread

## 컴포넌트 패턴

- 렌더링 중 계산 가능한 값은 파생(derive) — `useEffect`로 상태 동기화 금지
- 이벤트 기반 로직은 이벤트 핸들러에서 처리 — `useEffect` 남용 금지
- 리스트의 key는 안정적이고 고유해야 함 — 재정렬 가능한 리스트에서 배열 index를 key로 사용 금지
- prop drilling 2단계 초과 시 context 또는 composition 패턴 사용

## 성능

- `useMemo`/`useCallback`은 측정된 문제가 있거나 메모이된 자식에 전달할 때만 사용
- 렌더링 안에서 매번 새로 생성되는 객체/배열/함수를 메모이된 자식에 전달 금지

## TypeScript

- `any` 사용 금지 — `unknown` 사용 후 타입 가드로 좁힐 것
- 컴포넌트 props는 `interface`로 정의 — inline 타입 지양
- 이벤트 핸들러 타입은 React 제공 타입 사용 (`React.ChangeEvent<HTMLInputElement>` 등)
- 유니온 타입으로 상태를 표현할 때 discriminated union 사용
- `as` 타입 단언 최소화 — 타입 추론 또는 타입 가드 우선
