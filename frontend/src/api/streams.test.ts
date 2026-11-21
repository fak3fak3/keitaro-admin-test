import { createApi } from './client'
import { runStreamAction, type StreamAction } from './streams'

const STREAM = { id: 7, campaign_id: 1, name: 'Offers', type: 'default', position: 2,
  has_draft: false, has_conflicts: false, offers: [] }

function recordingApi() {
  const calls: { method: string; path: string; body: unknown }[] = []
  const api = createApi(async (input: RequestInfo | URL) => {
    const request = input as Request
    const text = await request.text()
    calls.push({
      method: request.method,
      path: new URL(request.url).pathname,
      body: text ? JSON.parse(text) : undefined,
    })
    return new Response(JSON.stringify(STREAM), { headers: { 'Content-Type': 'application/json' } })
  })
  return { api, calls }
}

test.each<[StreamAction, string, string, unknown]>([
  [{ kind: 'add', streamId: 7, offerId: 3 }, 'POST', '/api/streams/7/offers', { offer_id: 3 }],
  [{ kind: 'remove', streamId: 7, offerId: 3 }, 'POST', '/api/streams/7/offers/3/remove', undefined],
  [{ kind: 'bringBack', streamId: 7, offerId: 3 }, 'POST', '/api/streams/7/offers/3/bring-back', undefined],
  [{ kind: 'pin', streamId: 7, offerId: 3 }, 'POST', '/api/streams/7/offers/3/pin', undefined],
  [{ kind: 'unpin', streamId: 7, offerId: 3 }, 'POST', '/api/streams/7/offers/3/unpin', undefined],
  [{ kind: 'share', streamId: 7, offerId: 3, share: 40 }, 'PUT', '/api/streams/7/offers/3/share', { share: 40 }],
  [{ kind: 'resolve', streamId: 7, offerId: 3, keep: 'keitaro' }, 'POST', '/api/streams/7/offers/3/resolve', { keep: 'keitaro' }],
  [{ kind: 'resolveAll', streamId: 7, keep: 'mine' }, 'POST', '/api/streams/7/resolve', { keep: 'mine' }],
  [{ kind: 'acknowledge', streamId: 7 }, 'POST', '/api/streams/7/acknowledge', undefined],
  [{ kind: 'push', streamId: 7 }, 'POST', '/api/streams/7/push', undefined],
  [{ kind: 'cancel', streamId: 7 }, 'POST', '/api/streams/7/cancel', undefined],
])('%o → %s %s', async (action, method, path, body) => {
  const { api, calls } = recordingApi()

  const stream = await runStreamAction(api, action)

  expect(calls).toEqual([{ method, path, body }])
  expect(stream).toEqual(STREAM)
})
