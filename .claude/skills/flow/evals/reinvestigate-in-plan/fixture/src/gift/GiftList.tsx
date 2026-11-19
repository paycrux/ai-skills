import { Gift } from './types'
import { total } from './total'

export function GiftList({ gifts }: { gifts: Gift[] }) {
  return (
    <div>
      <ul>{gifts.map((g) => <li key={g.id}>{g.name} · {g.price}원{g.status === 'cancelled' ? ' (취소됨)' : ''}</li>)}</ul>
      <p>합계 {total(gifts)}원</p>
    </div>
  )
}
