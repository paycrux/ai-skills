import { test } from 'node:test'
import assert from 'node:assert/strict'
import { sortGifts } from './sort.js'

const gifts = [
  { id: 1, price: 3000, createdAt: 1 },
  { id: 2, price: 1000, createdAt: 2 },
  { id: 3, price: 1000, createdAt: 3 },
]

test('latest first by default', () => {
  assert.deepEqual(sortGifts(gifts).map((g) => g.id), [3, 2, 1])
})

test('lowest price first, newest first on a tie', () => {
  assert.deepEqual(sortGifts(gifts, 'price').map((g) => g.id), [3, 2, 1])
})
