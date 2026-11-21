import { createMutation, createQuery } from '@farfetched/core'
import { createEvent, createStore, sample } from 'effector'

import { errorText } from '@/api/errors'

import {
  fetchStreamsFx,
  listStreamsFx,
  type Stream,
  type StreamAction,
  streamActionFx,
} from '@/api/streams'

import { createOfferSearch } from './offerSearch'

/** Редактор офферов кампании (часть 2 ТЗ). Доли и черновик считает бэкенд — здесь только состояние UI. */
export const editorOpened = createEvent<number>()

export const $campaignId = createStore<number | null>(null).on(editorOpened, (_, id) => id)

export const streamsQuery = createQuery({ effect: listStreamsFx })

sample({ clock: editorOpened, target: streamsQuery.start })

/** Fetch streams from KT: бэкенд сливает Keitaro с черновиком и возвращает все потоки. */
export const fetchClicked = createEvent()
export const fetchMutation = createMutation({ effect: fetchStreamsFx })

sample({
  clock: fetchClicked,
  source: $campaignId,
  filter: (id): id is number => id !== null,
  target: fetchMutation.start,
})

/** Любая кнопка над потоком или оффером: Add, Remove, Pin, Push, решение конфликта и т.д. */
export const actionRequested = createEvent<StreamAction>()
export const actionMutation = createMutation({ effect: streamActionFx })

/** Потоки с запросом в работе. Ответ — поток целиком, поэтому два параллельных действия над одним
 * потоком могли бы прийти в обратном порядке и затереть друг друга: пока идёт запрос, поток заблокирован. */
export const $busyStreams = createStore<number[]>([])
  .on(actionMutation.start, (busy, { streamId }) => [...busy, streamId])
  .on(actionMutation.finished.finally, (busy, { params }) => busy.filter((id) => id !== params.streamId))

sample({
  clock: actionRequested,
  source: $busyStreams,
  filter: (busy, action) => !busy.includes(action.streamId),
  fn: (_, action) => action,
  target: actionMutation.start,
})

export const $streams = createStore<Stream[]>([])
  .on(streamsQuery.finished.success, (_, { result }) => result)
  .on(fetchMutation.finished.success, (_, { result }) => result)
  .on(actionMutation.finished.success, (streams, { result }) =>
    streams.map((stream) => (stream.id === result.id ? result : stream)),
  )
  .reset(editorOpened) // другая кампания: не показываем чужие потоки, пока грузятся свои

/** Одно сообщение об ошибке над потоками: 409/404 и ошибки Keitaro — текстом бэкенда. */
export const errorDismissed = createEvent()
export const $editorError = createStore<string | null>(null)
  .on(
    [
      streamsQuery.finished.failure,
      fetchMutation.finished.failure,
      actionMutation.finished.failure,
    ],
    (_, { error }) => errorText(error),
  )
  .reset(errorDismissed, streamsQuery.start, fetchMutation.start, actionMutation.start)

/** Add: поле поиска оффера открыто под одним потоком за раз, модель поиска общая. */
export const addOfferSearch = createOfferSearch()
export const addOpened = createEvent<number>()
export const addClosed = createEvent()
export const addSubmitted = createEvent()

const offerAdded = actionMutation.finished.success.filter({ fn: ({ params }) => params.kind === 'add' })

export const $addStreamId = createStore<number | null>(null)
  .on(addOpened, (_, streamId) => streamId)
  .reset(addClosed, offerAdded, editorOpened)

sample({ clock: [addOpened, addClosed, offerAdded], target: addOfferSearch.reset })

sample({
  clock: addSubmitted,
  source: { streamId: $addStreamId, offer: addOfferSearch.$selected },
  filter: ({ streamId, offer }) => streamId !== null && offer !== null,
  fn: ({ streamId, offer }): StreamAction => ({ kind: 'add', streamId: streamId!, offerId: offer!.id }),
  target: actionRequested,
})
