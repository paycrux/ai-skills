# Template Compliance Checklist

After writing all documents, verify each file before proceeding to evaluation.
If any check fails, rewrite that file immediately.

## README.md

- [ ] Contains `이슈:`, `생성일:`, `상태:` fields
- [ ] Has `배경`, `목표`, `범위` sections

## spec.md

- [ ] Has `화면/기능 흐름`, `상태 정의`, `엣지 케이스` sections
- [ ] (frontend) Has `상태 위치 결정` section with at least one table row

## findings.md

- [ ] Has `직접 관련` and `영향 범위` sections
- [ ] `직접 관련` has at least one file entry

## tasks.md

- [ ] Has at least one `## Phase N:` header
- [ ] Every checklist item includes a file path in backticks

## ui-spec.md (frontend only)

- [ ] Has `화면 구조`, `컴포넌트 분해`, `상태 × 표시 매트릭스`, `컴포넌트 재사용 맵` sections
- [ ] Component breakdown table has at least one row
