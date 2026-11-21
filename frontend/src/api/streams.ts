import { createEffect } from 'effector'

import { type createApi, type Schemas, unwrap } from './client'
import { api } from './index'

type Api = ReturnType<typeof createApi>
export type Stream = Schemas['StreamOut']
export type StreamOffer = Schemas['StreamOfferOut']
export type Keep = 'mine' | 'keitaro'

/** Действие над потоком в редакторе; каждое возвращает поток целиком. */
export type StreamAction =
  | { kind: 'add' | 'remove' | 'bringBack' | 'pin' | 'unpin'; streamId: number; offerId: number }
  | { kind: 'share'; streamId: number; offerId: number; share: number }
  | { kind: 'resolve'; streamId: number; offerId: number; keep: Keep }
  | { kind: 'resolveAll'; streamId: number; keep: Keep }
  | { kind: 'acknowledge' | 'push' | 'cancel'; streamId: number }

export async function runStreamAction(client: Api, action: StreamAction): Promise<Stream> {
  const stream = { stream_id: action.streamId }
  switch (action.kind) {
    case 'add':
      return unwrap(client.POST('/api/streams/{stream_id}/offers', {
        params: { path: stream },
        body: { offer_id: action.offerId },
      }))
    case 'remove':
      return unwrap(client.POST('/api/streams/{stream_id}/offers/{offer_id}/remove', {
        params: { path: { ...stream, offer_id: action.offerId } },
      }))
    case 'bringBack':
      return unwrap(client.POST('/api/streams/{stream_id}/offers/{offer_id}/bring-back', {
        params: { path: { ...stream, offer_id: action.offerId } },
      }))
    case 'pin':
      return unwrap(client.POST('/api/streams/{stream_id}/offers/{offer_id}/pin', {
        params: { path: { ...stream, offer_id: action.offerId } },
      }))
    case 'unpin':
      return unwrap(client.POST('/api/streams/{stream_id}/offers/{offer_id}/unpin', {
        params: { path: { ...stream, offer_id: action.offerId } },
      }))
    case 'share':
      return unwrap(client.PUT('/api/streams/{stream_id}/offers/{offer_id}/share', {
        params: { path: { ...stream, offer_id: action.offerId } },
        body: { share: action.share },
      }))
    case 'resolve':
      return unwrap(client.POST('/api/streams/{stream_id}/offers/{offer_id}/resolve', {
        params: { path: { ...stream, offer_id: action.offerId } },
        body: { keep: action.keep },
      }))
    case 'resolveAll':
      return unwrap(client.POST('/api/streams/{stream_id}/resolve', {
        params: { path: stream },
        body: { keep: action.keep },
      }))
    case 'acknowledge':
      return unwrap(client.POST('/api/streams/{stream_id}/acknowledge', { params: { path: stream } }))
    case 'push':
      return unwrap(client.POST('/api/streams/{stream_id}/push', { params: { path: stream } }))
    case 'cancel':
      return unwrap(client.POST('/api/streams/{stream_id}/cancel', { params: { path: stream } }))
  }
}

export const streamActionFx = createEffect((action: StreamAction) => runStreamAction(api, action))

export const listStreamsFx = createEffect((campaignId: number) =>
  unwrap(api.GET('/api/campaigns/{campaign_id}/streams', { params: { path: { campaign_id: campaignId } } })),
)

export const fetchStreamsFx = createEffect((campaignId: number) =>
  unwrap(api.POST('/api/campaigns/{campaign_id}/fetch', { params: { path: { campaign_id: campaignId } } })),
)
