import type { GiftListResponse } from './types.ts'

export type Direction = 'RECEIVED' | 'SENT'
export type Period = '1M' | '3M'

export async function fetchGifts(direction: Direction, period: Period, cursor?: string): Promise<GiftListResponse> {
  const q = new URLSearchParams({ direction, period, ...(cursor ? { cursor } : {}) })
  const res = await fetch(`/v1/gifts?${q}`)
  return res.json()
}
