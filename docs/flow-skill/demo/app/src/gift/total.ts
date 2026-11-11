import type { Gift } from './types.ts'

export function total(gifts: Gift[]): number {
  return gifts.slice(1).reduce((sum, g) => sum + g.price, 0)
}
