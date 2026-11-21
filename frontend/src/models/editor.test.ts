import { allSettled, fork } from 'effector'

import { ApiError } from '@/api/client'
import { fetchStreamsFx, listStreamsFx, streamActionFx } from '@/api/streams'
import { GEO, OFFERS, offer, stream } from '@/test/streams'

import {
  $addStreamId,
  $busyStreams,
  addOfferSearch,
  addOpened,
  addSubmitted,
  $editorError,
  $streams,
  actionRequested,
  editorOpened,
  errorDismissed,
  fetchClicked,
} from './editor'

const CAMPAIGN = 217109

function editorScope(handlers: {
  list?: (id: number) => Promise<unknown>
  fetch?: (id: number) => Promise<unknown>
  action?: (action: unknown) => Promise<unknown>
} = {}) {
  return fork({
    handlers: [
      [listStreamsFx, handlers.list ?? (async () => [GEO, OFFERS])],
      [fetchStreamsFx, handlers.fetch ?? (async () => [GEO, OFFERS])],
      [streamActionFx, handlers.action ?? (async () => { throw new Error('не ожидалось') })],
    ],
  })
}

test('открытие редактора загружает потоки кампании из нашей БД', async () => {
  const asked: number[] = []
  const scope = editorScope({ list: async (id) => { asked.push(id); return [GEO, OFFERS] } })

  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  expect(asked).toEqual([CAMPAIGN])
  expect(scope.getState($streams)).toEqual([GEO, OFFERS])
})

test('Fetch забирает потоки из Keitaro и заменяет показанные', async () => {
  const merged = stream(OFFERS.id, [offer(3749, 50), offer(3717, 50)])
  const fetched: number[] = []
  const scope = editorScope({ fetch: async (id) => { fetched.push(id); return [GEO, merged] } })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(fetchClicked, { scope })

  expect(fetched).toEqual([CAMPAIGN])
  expect(scope.getState($streams)).toEqual([GEO, merged])
})

test('действие отправляется на бэкенд и заменяет только свой поток', async () => {
  const afterRemove = stream(OFFERS.id, [
    offer(3749, 50, { changed: true }),
    offer(3717, 0, { status: 'removed', changed: true }),
    offer(11111, 50, { changed: true }),
  ], { has_draft: true })
  const sent: unknown[] = []
  const scope = editorScope({ action: async (action) => { sent.push(action); return afterRemove } })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(actionRequested, {
    scope,
    params: { kind: 'remove', streamId: OFFERS.id, offerId: 3717 },
  })

  expect(sent).toEqual([{ kind: 'remove', streamId: OFFERS.id, offerId: 3717 }])
  expect(scope.getState($streams)).toEqual([GEO, afterRemove])
})

test('пока действие выполняется, поток заблокирован; соседние — нет', async () => {
  let finish: (() => void) | undefined
  const scope = editorScope({
    action: () => new Promise((resolve) => { finish = () => resolve(OFFERS) }),
  })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  const pushed = allSettled(actionRequested, { scope, params: { kind: 'push', streamId: OFFERS.id } })
  await vi.waitFor(() => expect(finish).toBeDefined())
  expect(scope.getState($busyStreams)).toEqual([OFFERS.id])

  finish!()
  await pushed
  expect(scope.getState($busyStreams)).toEqual([])
})

test('действие над заблокированным потоком не отправляется', async () => {
  let finish: (() => void) | undefined
  const sent: unknown[] = []
  const scope = editorScope({
    action: (action) => {
      sent.push(action)
      return new Promise((resolve) => { finish = () => resolve(OFFERS) })
    },
  })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  const pushed = allSettled(actionRequested, { scope, params: { kind: 'push', streamId: OFFERS.id } })
  await vi.waitFor(() => expect(finish).toBeDefined())
  void allSettled(actionRequested, { scope, params: { kind: 'cancel', streamId: OFFERS.id } })
  finish!()
  await pushed

  expect(sent).toEqual([{ kind: 'push', streamId: OFFERS.id }])
})

test('ошибка действия показывается сообщением бэкенда и закрывается', async () => {
  const conflict = 'Решите конфликты с Keitaro по офферам 3749, затем Push'
  const scope = editorScope({ action: async () => { throw new ApiError(409, conflict) } })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(actionRequested, { scope, params: { kind: 'push', streamId: OFFERS.id } })
  expect(scope.getState($editorError)).toBe(conflict)
  expect(scope.getState($streams)).toEqual([GEO, OFFERS]) // поток не тронут

  await allSettled(errorDismissed, { scope })
  expect(scope.getState($editorError)).toBeNull()
})

test('ошибка Fetch тоже показывается', async () => {
  const scope = editorScope({
    fetch: async () => { throw new ApiError(502, 'Keitaro API error (401): Invalid API key') },
  })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(fetchClicked, { scope })

  expect(scope.getState($editorError)).toBe('Keitaro API error (401): Invalid API key')
})

test('Add: выбранный в поиске оффер добавляется в поток, поле закрывается', async () => {
  const withFour = stream(OFFERS.id, [...OFFERS.offers, offer(11112, 25, { published_status: null, published_share: null, changed: true })], { has_draft: true })
  const sent: unknown[] = []
  const scope = editorScope({ action: async (action) => { sent.push(action); return withFour } })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(addOpened, { scope, params: OFFERS.id })
  await allSettled(addOfferSearch.offerSelected, { scope, params: { id: 11112, name: 'Oxys' } })
  await allSettled(addSubmitted, { scope })

  expect(sent).toEqual([{ kind: 'add', streamId: OFFERS.id, offerId: 11112 }])
  expect(scope.getState($streams)[1]).toEqual(withFour)
  expect(scope.getState($addStreamId)).toBeNull()
  expect(scope.getState(addOfferSearch.$selected)).toBeNull()
})

test('Add без выбранного оффера ничего не отправляет', async () => {
  const scope = editorScope()
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  await allSettled(addOpened, { scope, params: OFFERS.id })
  await allSettled(addSubmitted, { scope }) // обработчик действия бросил бы ошибку

  expect(scope.getState($editorError)).toBeNull()
  expect(scope.getState($addStreamId)).toBe(OFFERS.id)
})

test('при открытии другой кампании потоки прошлой не показываются, пока грузятся новые', async () => {
  let finish: (() => void) | undefined
  const scope = editorScope({
    list: (id) => id === CAMPAIGN
      ? Promise.resolve([GEO, OFFERS])
      : new Promise((resolve) => { finish = () => resolve([]) }),
  })
  await allSettled(editorOpened, { scope, params: CAMPAIGN })

  const opening = allSettled(editorOpened, { scope, params: 217519 })
  await vi.waitFor(() => expect(finish).toBeDefined())
  expect(scope.getState($streams)).toEqual([])
  finish!()
  await opening
})
