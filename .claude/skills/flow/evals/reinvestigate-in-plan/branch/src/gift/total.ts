import { Gift } from './types'

export function total(gifts: Gift[]): number {
  return gifts.reduce((sum, g) => sum + g.price, 0)
}
