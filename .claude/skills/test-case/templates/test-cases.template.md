# 테스트 케이스 — {기능명}

> 출처: {task-plan 폴더 | 파일 경로 | "사용자 설명"}
> 작성일: {오늘 날짜}
> 대상 URL: {base-url}{path} (알 수 있는 경우)

---

## 테스트 환경

### 사전 조건

## <!-- 로그인 요구사항, 필요한 권한, 기기/브라우저 요구사항 나열 -->

### 테스트 데이터

## <!-- 필요한 구체적 데이터: 계정, 상품, 설정 등 -->

---

## TC-{N}: {테스트 케이스 제목}

> 목적: {이 테스트가 검증하는 내용 — 1줄}

### 초기 상태

## <!-- 이 테스트 시작 전 필요한 앱/페이지 상태 -->

### 단계

| #   | 완료 | 액션   | 대상                            | 기대 결과         |
| --- | ---- | ------ | ------------------------------- | ----------------- |
| 1   | [ ]  | {동사} | `{selector-hint}` {설명}        | {구체적인 결과}   |

<!--
액션 동사 (이것만 사용):
  navigate, click, type, select, toggle, scroll,
  wait, verify, hover, drag, upload

셀렉터 힌트 우선순위:
  1. data-testid="xxx"
  2. role="button" name="Save"
  3. text="Save Changes"
  4. .class-name 또는 #id
  5. {중괄호 안에 자연어 설명}
-->

### 검증 포인트

<!-- 모든 단계 완료 후 확인할 검증 항목 -->

- [ ] {체크포인트}

---

## 조합 매트릭스

### CM-{N}: {기능명} — {조건 그룹}

<!--
규칙:
  - 조건 2개 → 전수 조합 (2×2, 2×3 등)
  - 조건 3개 이상 → 페어와이즈 조합
  - 모든 행은 해당 조합을 커버하는 TC와 연결
  - 커버하는 TC가 없으면 새로 생성
-->

| 조건 A | 조건 B | 기대 결과 | 관련 TC |
| ------ | ------ | --------- | ------- |
|        |        |           | TC-{N}  |

---

## 자동화 메타데이터

```yaml
feature: { feature-name }
base_url: { base-url or "TBD" }
auth_required: { true/false }
test_data:
  - type: { data type }
    description: { description }
selectors:
  - name: { element name }
    hint: { CSS selector or data-testid or role description }
    type: { button | input | link | text | checkbox | select }
```
