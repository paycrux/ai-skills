export type GiftStatus = 'USABLE' | 'USED' | 'EXPIRED' | 'REFUNDED'

export interface Gift {
  id: string
  name: string
  price: number
  status: GiftStatus
  senderPhoneMasked: string
  receivedAt: string
}

export interface GiftListResponse {
  items: Gift[]
  nextCursor: string | null
}
