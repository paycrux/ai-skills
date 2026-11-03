import { Gift } from './types'

export function GiftList({ gifts }: { gifts: Gift[] }) {
  return <ul>{gifts.map((g) => <li key={g.id}>{g.name} · {g.price}원</li>)}</ul>
}
