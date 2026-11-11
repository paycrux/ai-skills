import { Gift } from './types'

export async function fetchGifts(): Promise<Gift[]> {
  const res = await fetch('/api/gifts')
  return res.json()
}
