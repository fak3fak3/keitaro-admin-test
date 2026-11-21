import type { Stream, StreamOffer } from '@/api/streams'

/** Тестовые данные редактора в формате нашего API. */
export function offer(offerId: number, share: number, extra: Partial<StreamOffer> = {}): StreamOffer {
  return {
    offer_id: offerId,
    offer_name: `Offer ${offerId}`,
    status: 'active',
    share,
    pinned: false,
    changed: false,
    published_status: 'active',
    published_share: share,
    keitaro_change: null,
    keitaro_share_before: null,
    conflict: false,
    ...extra,
  }
}

export function stream(id: number, offers: StreamOffer[], extra: Partial<Stream> = {}): Stream {
  return {
    id,
    campaign_id: 217109,
    name: offers.length ? 'Offers' : 'Geo AU → Google',
    type: offers.length ? 'default' : 'regular',
    position: offers.length ? 2 : 1,
    has_draft: false,
    has_conflicts: false,
    offers,
    ...extra,
  }
}

export const GEO = stream(1333642, [])
export const OFFERS = stream(1333643, [offer(3749, 34), offer(3717, 33), offer(11111, 33)])
