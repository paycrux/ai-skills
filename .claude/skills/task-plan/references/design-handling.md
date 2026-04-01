# Design Reference Handling

## Figma Link

```
Is Figma MCP server available? (check tool list for figma/design tools)
├── YES → fetch design data via MCP
│   - Extract screen structure, component hierarchy, spacing, colors
│   - Record in ui-spec.md and findings.md
└── NO → notify user:
    "Figma MCP 서버가 연결되어 있지 않습니다.
     다음 중 하나를 제공해주세요:
     - 화면별 스크린샷
     - 디자인 스펙 (컴포넌트 구조, 간격, 색상 등)
     - 또는 Figma MCP 서버를 설정해주세요"
    → wait for user input before proceeding
```

## Design Reference Availability

```
Does the task have a design reference? (Figma, screenshots, design spec)
├── YES → follow the provided design faithfully
│   - Colors, spacing, typography, layout from the design source
│   - Record design source in ui-spec.md header
└── NO → apply `.claude/rules/frontend-design.md` during implementation
    - Prevents AI slop (generic fonts, cliché color schemes)
    - Forces context-appropriate design choices
    - Mark in ui-spec.md: "디자인 레퍼런스 없음"
```
