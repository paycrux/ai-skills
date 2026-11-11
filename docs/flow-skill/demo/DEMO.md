# flow 시연 대본

시연용 가짜 레포입니다. 기획서 · Jira · Slack · Figma는 모두 `demo-inputs/`의 가짜 파일이고, 링크 대신 이 파일을 읽게 합니다.
다시 처음 상태로 돌리려면 ai-skills 레포에서 `bash docs/flow-skill/demo/setup.sh`를 다시 실행합니다.

## 시연 1 · 간단한 버그 (링크 없이 설명만)

```bash
git switch -c fix/gift-total
claude
```

붙여 넣을 말:

```
/flow 선물내역 위의 "받은 선물 합계"가 실제보다 적게 나와. 선물 5개면 4개 값만 더해지는 것 같아.
```

보여 줄 것:

- flow가 기존 도메인 `docs/gift`를 찾아 `버그 수정` 작업을 `tasks` 단계 하나로 만든다
- 03 계획의 첫 항목이 재현 테스트다. 테스트를 먼저 쓰고 실패하는 걸 본다 (`npm test`)
- 계획 승인에서 멈춘다 → "승인"이라고 답하면 `src/gift/total.ts`를 고치고 테스트가 통과한다
- 원인: `total.ts`가 `gifts.slice(1)`로 첫 선물을 건너뛴다

## 시연 2 · 큰 작업 (기획서 · Figma · Jira · Slack을 함께)

```bash
git switch main && git switch -c feat/GIFT-201
claude
```

붙여 넣을 말:

```
/flow GIFT-201 선물내역 받은 선물 목록.
시연이라 링크 대신 파일을 줄게.
- 기획서: demo-inputs/prd.md
- Jira: demo-inputs/jira-GIFT-201.md
- Slack 스레드: demo-inputs/slack-thread.md
- Figma: 노드 2507:17556. Figma MCP는 부르지 말고 demo-inputs/figma/gift-list.png 를 get_screenshot 결과로, gift-list.xml 을 get_metadata 결과(이미 펼친 것)로 써.
01 기획 · 화면과 02 질문까지 진행하고 질문에서 멈춰.
```

보여 줄 것:

- 01: 화면에 핀이 찍힌 SOT 맵. 카드 요소가 `sample-response.json`의 `senderPhoneMasked` · `status` · `receivedAt`에 이어진다
- 02: 기획서가 비워 둔 칸이 질문으로 나온다. 심어 둔 빈칸은 세 개다
  - 사용 가능만 보기: 서버 필터(`usableOnly`, 다음 스프린트) vs 프론트에서 거르기 (Slack)
  - 환불 표기: 기획서 `[환불]` vs 디자인 `[환불(취소)]` (Slack)
  - 받은 선물이 없을 때의 화면 (기획서 "미정")
- 질문 페이지에서 답을 고르고 채팅에 "답 썼어" → 결정이 기획 · SOT 맵에 반영된다
- 이어서 "03 계획 써 줘" → 계획 승인에서 멈춘다

## 시간이 모자랄 때

- 시연 2는 01 단계(화면 읽기)에 몇 분 걸린다. 발표 전에 한 번 돌려 두고, 그 브랜치를 그대로 열어 02 질문부터 보여 줘도 된다
- 페이지 열기: `python3 ~/.claude/skills/flow/scripts/flow.py open docs/gift/index.html`
