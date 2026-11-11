export const SORTS = ['latest', 'price']

export function sortGifts(gifts, sort = 'latest') {
  const copy = [...gifts]
  if (sort === 'price') return copy.sort((a, b) => a.price - b.price || b.createdAt - a.createdAt)
  return copy.sort((a, b) => b.createdAt - a.createdAt)
}
