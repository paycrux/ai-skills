import type { Gift } from './types.ts'
import { total } from './total.ts'

interface GiftListProps {
  gifts: Gift[]
}

export function GiftList({ gifts }: GiftListProps) {
  return (
    <section>
      <p>받은 선물 합계 {total(gifts)}원</p>
      <ul>
        {gifts.map((g) => (
          <li key={g.id}>
            <span>{g.senderPhoneMasked}님이 보낸 선물</span>
            <b>{g.name}</b>
            <time>{g.receivedAt}</time>
          </li>
        ))}
      </ul>
    </section>
  )
}
